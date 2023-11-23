# ---------------------------------------------------------------------
# Gufo ACME: AcmeClient implementation
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""An AcmeClient implementation."""
# Python modules
import asyncio
import json
import random
from types import TracebackType
from typing import (
    Any,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

# Third-party modules
import httpx
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)
from cryptography.x509.oid import NameOID
from josepy.errors import DeserializationError
from josepy.json_util import decode_b64jose, encode_b64jose
from josepy.jwa import HS256, RS256, JWASignature
from josepy.jwk import JWK, JWKRSA, JWKOct

# Gufo ACME modules
from .. import __version__
from ..acme import AcmeJWS
from ..error import (
    AcmeAlreadyRegistered,
    AcmeAuthorizationError,
    AcmeBadNonceError,
    AcmeCertificateError,
    AcmeConnectError,
    AcmeError,
    AcmeExternalAccountRequred,
    AcmeFulfillmentFailed,
    AcmeNotRegistredError,
    AcmeRateLimitError,
    AcmeTimeoutError,
    AcmeUnauthorizedError,
    AcmeUndecodableError,
)
from ..log import logger
from ..types import (
    AcmeAuthorization,
    AcmeChallenge,
    AcmeDirectory,
    AcmeOrder,
    ExternalAccountBinding,
)

BAD_REQUEST = 400
T = TypeVar("T")
CT = TypeVar("CT", bound="AcmeClient")


class AcmeClient(object):
    """
    ACME Client.

    Examples:
    Create new account:
    ``` python
    async with AcmeClient(directory, key=key) as client:
        uri = await client.new_account("test@example.com")
    ```
    Sign an CSR:
    ``` python
    class SignClient(AcmeClient):
        async def fulfill_http_01(
            self, domain: str, challenge: AcmeChallenge
        ) -> bool:
            # do something useful
            return True

    async with SignClient(directory, key=key, account_url=uri) as client:
        cert = await client.sign("example.com", csr)
    ```

    Attributes:
        JOSE_CONTENT_TYPE: Content type for JOSE requests.
        NONCE_HEADER: Name of the HTTP response header
            containing nonce.
        RETRY_AFTER_HEADER: Name of the HTTP reponse header
            containing required retry delay.
        DEFAULT_TIMEOUT: Default network requests timeout, in seconds.

    Args:
        directory_url: An URL to ACME directory.
        key: JWK private key. The compatible key may be generated
            by the [gufo.acme.clients.base.AcmeClient.get_key][] function.
        alg: Signing algorithm to use.
        account_url: Optional ACME account URL, cotaining the
            stored result of the previous call to the
            [gufo.acme.clients.base.AcmeClient.new_account][] function.
        timeout: Network requests timeout in seconds.
        user_agent: Override default User-Agent header.
    """

    JOSE_CONTENT_TYPE: str = "application/jose+json"
    NONCE_HEADER: str = "Replay-Nonce"
    RETRY_AFTER_HEADER: str = "Retry-After"
    DEFAULT_TIMEOUT: float = 40.0
    DEFAULT_SIGNATURE = RS256

    def __init__(
        self: "AcmeClient",
        directory_url: str,
        *,
        key: JWK,
        alg: Optional[JWASignature] = None,
        account_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self._directory_url = directory_url
        self._directory: Optional[AcmeDirectory] = None
        self._key = key
        self._alg = alg or self.DEFAULT_SIGNATURE
        self._account_url = account_url
        self._nonces: Set[bytes] = set()
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._user_agent = user_agent or f"Gufo ACME/{__version__}"

    async def __aenter__(self: CT) -> CT:
        """
        An asynchronous context manager.

        Examples:
            ``` py
            async with AcmeClient(....) as client:
                ...
            ```
        """
        return self

    async def __aexit__(
        self: "AcmeClient",
        exc_t: Optional[Type[BaseException]],
        exc_v: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Asynchronous context exit."""
        return

    def is_bound(self: "AcmeClient") -> bool:
        """
        Check if the client is bound to the account.

        The client may be bound to account either:

        * By setting `account_url` in constructor.
        * By calling [gufo.acme.clients.base.AcmeClient.new_account][]

        Returns:
            True - if the client is bound to account,
                False - otherwise.
        """
        return self._account_url is not None

    def _check_bound(self: "AcmeClient") -> None:
        """
        Check the client is bound to account.

        Raises:
            AcmeNotRegistredError: if client is not bound.
        """
        if not self.is_bound():
            raise AcmeNotRegistredError

    def _check_unbound(self: "AcmeClient") -> None:
        """
        Check the client is not  bound to account.

        Raises:
            AcmeAlreadyRegistered: if client is bound.
        """
        if self.is_bound():
            raise AcmeAlreadyRegistered

    def _get_client(self: "AcmeClient") -> httpx.AsyncClient:
        """
        Get a HTTP client instance.

        May be overrided in subclasses to configure
        or replace httpx.AsyncClient.

        Returns:
            Async HTTP client instance.
        """
        return httpx.AsyncClient(
            http2=True, headers={"User-Agent": self._user_agent}
        )

    @staticmethod
    async def _wait_for(fut: Coroutine[Any, Any, T], timeout: float) -> T:
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError as e:
            raise AcmeTimeoutError from e

    async def _get_directory(self: "AcmeClient") -> AcmeDirectory:
        """
        Get and ACME directory.

        Caches response to fetch request only once.

        Returns:
            AcmeDirectory instance containing URLs
            for ACME server.

        Raises:
            AcmeError: In case of the errors.
        """
        if self._directory is not None:
            return self._directory
        async with self._get_client() as client:
            logger.warning(
                "Fetching ACME directory from %s", self._directory_url
            )
            try:
                r = await self._wait_for(
                    client.get(self._directory_url), self._timeout
                )
            except httpx.HTTPError as e:
                raise AcmeConnectError from e
            self._check_response(r)
            data = r.json()
        external_account_required = False
        if "meta" in data:
            external_account_required = data["meta"].get(
                "externalAccountRequired", False
            )
        self._directory = AcmeDirectory(
            new_account=data["newAccount"],
            new_nonce=data.get("newNonce"),
            new_order=data["newOrder"],
            external_account_required=external_account_required,
        )
        return self._directory

    @staticmethod
    def _email_to_contacts(email: Union[str, Iterable[str]]) -> List[str]:
        """
        Convert email to list of contacts.

        Args:
            email: String containing email or any iterable yielding emails.

        Returns:
            RFC-8555 pp. 7.1.2 contact structure.
        """
        if isinstance(email, str):
            return [f"mailto:{email}"]
        return [f"mailto:{m}" for m in email]

    @staticmethod
    def decode_auto_base64(data: str) -> bytes:
        """
        Decode Base64/Base64 URL.

        Auto-detect encoding.

        Args:
            data: Encoded text.

        Returns:
            Decoded bytes.
        """
        # Base64 URL -> Base64
        data = data.replace("-", "+").replace("_", "/")
        return decode_b64jose(data)

    def _get_eab(
        self: "AcmeClient", external_binding: ExternalAccountBinding, url: str
    ) -> Dict[str, Any]:
        """
        Get externalAccountBinding field.

        Args:
            external_binding: External binding structure.
            url: newAccount url.
        """
        payload = json.dumps(self._key.public_key().to_partial_json()).encode()
        return AcmeJWS.sign(
            payload,
            key=JWKOct(key=external_binding.hmac_key),
            alg=HS256,
            url=url,
            kid=external_binding.kid,
        ).to_partial_json()

    async def new_account(
        self: "AcmeClient",
        email: Union[str, Iterable[str]],
        *,
        external_binding: Optional[ExternalAccountBinding] = None,
    ) -> str:
        """
        Create new account.

        Performs RFC-8555 pp. 7.3 call to create new account.
        The account will be bind to the used key.

        Examples:
            Create an account with single contact email:

            ``` python
            async with AcmeClient(directory, key=key) as client:
                uri = await client.new_account("test@example.com")
            ```

            Create an account with multiple contact emails:

            ``` python
            async with AcmeClient(directory, key=key) as client:
                uri = await client.new_account([
                    "ca@example.com",
                    "boss@example.com"
                ])
            ```

        Args:
            email: String containing email or any iterable yielding emails.
            external_binding: External account binding, if required.

        Returns:
            ACME account url which can be passed as `account_url` parameter
                to the ACME client.

        Raises:
            AcmeError: In case of the errors.
            AcmeAlreadyRegistered: If an client is already bound to account.
            AcmeExternalAccountRequred: External account binding is required.
        """
        # Build contacts
        contacts = self._email_to_contacts(email)
        logger.warning("Creating new account: %s", ", ".join(contacts))
        # Check the client is not already bound
        self._check_unbound()
        # Refresh directory
        d = await self._get_directory()
        # Check if external account binding is required
        if d.external_account_required and not external_binding:
            raise AcmeExternalAccountRequred()
        # Prepare request
        req: Dict[str, Any] = {
            "termsOfServiceAgreed": True,
            "contact": contacts,
        }
        if d.external_account_required and external_binding:
            req["externalAccountBinding"] = self._get_eab(
                external_binding=external_binding, url=d.new_account
            )
        # Post request
        resp = await self._post(
            d.new_account,
            req,
        )
        self._account_url = resp.headers["Location"]
        return self._account_url

    async def deactivate_account(self: "AcmeClient") -> None:
        """
        Deactivate account.

        Performs RFC-8555 pp. 7.3.6 call to deactivate an account.
        A deactivated account can no longer request certificate
        issuance or access resources related to the account,
        such as orders or authorizations.

        To call `deactivate_account` AcmeClient must be bound
        to acount either via `account_url` option or
        via `new_account` call. After successfully processing
        a client will be unbound from account.

        Examples:
            Deactivate account:

            ``` python
            async with AcmeClient(
                directory, key=key,
                account_url=url
            ) as client:
                uri = await client.deactivate_account()
            ```

        Raises:
            AcmeError: In case of the errors.
            AcmeNotRegistred: If the client is not bound to account.
        """
        logger.warning("Deactivating account: %s", self._account_url)
        # Check account is really bound
        self._check_bound()
        # Send deactivation request
        await self._post(
            self._account_url,  # type: ignore
            {"status": "deactivated"},
        )
        # Unbind client
        self._account_url = None

    @staticmethod
    def _domain_to_identifiers(
        domain: Union[str, Iterable[str]]
    ) -> List[Dict[str, str]]:
        """
        Convert domain name to a list of order identifiers.

        Args:
            domain: String containing domain or any iterable yielding domains.

        Returns:
            RFC-8555 pp. 7.1.3 identifiers structure.

        """
        if isinstance(domain, str):
            return [{"type": "dns", "value": domain}]
        return [{"type": "dns", "value": d} for d in domain]

    async def new_order(
        self: "AcmeClient", domain: Union[str, Iterable[str]]
    ) -> AcmeOrder:
        """
        Create new order.

        Performs RFC-8555 pp. 7.4 order creation sequence.
        Before creating a new order any of the prerequisites must be met.

        * `new_accout()` function called.
        * `account_url` passed to constructor.

        Examples:
            Order for single domain:

            ``` python
            async with AcmeClient(
                directory,
                key=key,
                account_url=account_url
            ) as client:
                order = await client.new_order("example.com")
            ```

            Order for multiple domains:

            ``` py
            async with AcmeClient(
                directory,
                key=key,
                account_url=account_url
            ) as client:
                order = await client.new_order([
                    "example.com",
                    "sub.example.com"
                ])
            ```

        Args:
            domain: String containing domain or an iterable
                yielding domains.

        Returns:
            An AcmeOrder object.

        Raises:
            AcmeError: In case of the errors.
        """
        # Expand identifiers
        identifiers = self._domain_to_identifiers(domain)
        logger.warning(
            "Creating new order: %s",
            ", ".join(d["value"] for d in identifiers),
        )
        self._check_bound()
        # Refresh directory
        d = await self._get_directory()
        # Post request
        resp = await self._post(d.new_order, {"identifiers": identifiers})
        data = resp.json()
        #
        return AcmeOrder(
            authorizations=[
                AcmeAuthorization(domain=i["value"], url=a)
                for i, a in zip(identifiers, data["authorizations"])
            ],
            finalize=data["finalize"],
        )

    async def get_challenges(
        self: "AcmeClient", auth: AcmeAuthorization
    ) -> List[AcmeChallenge]:
        """
        Get a challenge for an authoriations.

        Performs RFC-8555 pp. 7.5 sequence.

        Examples:
            ``` python
            async with AcmeClient(
                directory,
                key=key,
                account_url=account_url
            ) as client:
                order = await client.new_order([
                    "example.com",
                    "sub.example.com"
                ])
                for auth in order.authorizations:
                    challenges = await client.get_challenges(auth)
            ```

        Args:
            auth: AcmeAuthorization object, usually from
                AcmeOrder.authorizations.

        Returns:
            List of AcmeChallenge.

        Raises:
            AcmeError: In case of the errors.
        """
        logger.warning("Getting challenges for %s", auth.domain)
        self._check_bound()
        resp = await self._post(auth.url, None)
        data = resp.json()
        return [
            AcmeChallenge(type=d["type"], url=d["url"], token=d["token"])
            for d in data["challenges"]
        ]

    async def respond_challenge(
        self: "AcmeClient", challenge: AcmeChallenge
    ) -> None:
        """
        Respond to challenge.

        Responding to challenge means the client performed
        all fulfillment tasks and ready to prove
        the challenge.

        Args:
            challenge: ACME challenge as returned by
                `get_challenges` function.
        """
        logger.warning("Responding challenge %s", challenge.type)
        self._check_bound()
        await self._post(challenge.url, {})

    async def wait_for_authorization(
        self: "AcmeClient", auth: AcmeAuthorization
    ) -> None:
        """
        Wait untill authorization became valid.

        Args:
            auth: ACME Authorization
        """
        while True:
            logger.warning("Polling authorization for %s", auth.domain)
            self._check_bound()
            resp = await self._post(auth.url, None)
            data = resp.json()
            status = data.get("status") or "pending"
            logger.warning(
                "Authorization status for %s is %s", auth.domain, status
            )
            if status == "valid":
                return
            if status == "pending":
                await self._random_delay(3.0)
            else:
                msg = f"Status is {status}"
                raise AcmeAuthorizationError(msg)

    @staticmethod
    async def _random_delay(limit: float) -> None:
        """
        Wait for random time.

        Sleep for random time from interval
        from [limit/2 .. limit]

        Args:
            limit: Maximal delay in seconds.
        """
        hl = limit / 2.0
        r = random.random()  # noqa: S311
        await asyncio.sleep(hl + hl * r)

    @staticmethod
    def _pem_to_der(pem: bytes) -> bytes:
        """
        Convert CSR from PEM to DER format.

        Args:
            pem: CSR in PEM format.

        Returns:
            CSR in DER format.
        """
        csr = x509.load_pem_x509_csr(pem)
        return csr.public_bytes(encoding=Encoding.DER)

    @staticmethod
    def _get_order_status(resp: httpx.Response) -> str:
        """
        Check order response.

        Args:
            resp: Order response

        Returns:
            Order status

        Raises:
            AcmeCertificateError: if status is invalid
        """
        data = resp.json()
        status = cast(str, data["status"])
        if status == "invalid":
            msg = "Failed to finalize order"
            raise AcmeCertificateError(msg)
        return status

    async def finalize_and_wait(
        self: "AcmeClient", order: AcmeOrder, *, csr: bytes
    ) -> bytes:
        """
        Send finalization request and wait for the certificate.

        Args:
            order: ACME Order.
            csr: CSR in PEM format.

        Returns:
            Signed certificate in PEM format.

        Raises:
            AcmeCertificateError: When server refuses
                to sign the certificate.
        """
        logger.warning("Finalizing order")
        self._check_bound()
        resp = await self._post(
            order.finalize, {"csr": encode_b64jose(self._pem_to_der(csr))}
        )
        self._get_order_status(resp)
        order_uri = resp.headers["Location"]
        # Poll for certificate
        await self._random_delay(1.0)
        while True:
            logger.warning("Polling order")
            resp = await self._post(order_uri, None)
            status = self._get_order_status(resp)
            if status == "valid":
                logger.warning("Order is ready. Downloading certificate")
                data = resp.json()
                resp = await self._post(data["certificate"], None)
                return resp.text.encode()

    async def sign(self: "AcmeClient", domain: str, csr: bytes) -> bytes:
        """
        Sign the CSR and get a certificate for domain.

        An orchestration function to perform full ACME sequence,
        starting from order creation and up to the certificate
        fetching.

        Should be used inn subclasses which override one
        or more of `fulfull_*` functions, and, optionaly,
        `clean_*` functions.

        Examples:
            ``` python
            class SignClient(AcmeClient):
                async def fulfill_http_01(
                    self, domain: str, challenge: AcmeChallenge
                ) -> bool:
                    # do something useful
                    return True

            async with SignClient(
                directory,
                key=key,
                account_url=uri
            ) as client:
                cert = await client.sign("example.com", csr)
            ```

        Returns:
            The signed certificate in PEM format.

        Raises:
            AcmeTimeoutError: On timeouts.
            AcmeFulfillmentFailed: If the client failed to
                fulfill any challenge.
            AcmeError: and subclasses in case of other errors.
        """
        logger.warning("Signing CSR for domain %s", domain)
        self._check_bound()
        # Create order
        order = await self.new_order(domain)
        # Process authorizations
        for auth in order.authorizations:
            logger.warning("Processing authorization for %s", auth.domain)
            # Get challenges
            challenges = await self.get_challenges(auth)
            fulfilled_challenge = None
            for ch in challenges:
                if await self.fulfill_challenge(domain, ch):
                    await self.respond_challenge(ch)
                    fulfilled_challenge = ch
                    break
            else:
                raise AcmeFulfillmentFailed
            # Wait for authorization became valid
            await self._wait_for(self.wait_for_authorization(auth), 60.0)
            # Clear challenge
            await self.clear_challenge(domain, fulfilled_challenge)
        # Finalize order and get certificate
        return await self._wait_for(
            self.finalize_and_wait(order, csr=csr), 60.0
        )

    async def _head(self: "AcmeClient", url: str) -> httpx.Response:
        """
        Perform HTTP HEAD request.

        Performs HTTP HEAD request using underlied HTTP client.
        Updates nonces if any responded.

        Args:
            url: Request URL

        Returns:
            httpx.Response instance.

        Raises:
            AcmeError: in case of error.
        """
        logger.warning("HEAD %s", url)
        async with self._get_client() as client:
            try:
                r = await self._wait_for(
                    client.head(url),
                    self._timeout,
                )
            except httpx.HTTPError as e:
                raise AcmeConnectError from e
            self._check_response(r)
            self._nonce_from_response(r)
            return r

    async def _post(
        self: "AcmeClient", url: str, data: Optional[Dict[str, Any]]
    ) -> httpx.Response:
        """
        Perform HTTP POST request.

        Performs HTTP POST request using underlied HTTP client.
        Updates nonces if any responded. Retries once
        if the nonce was rejected by server.
        Raises an AcmeError in case of the error.

        Args:
            url: Request URL
            data: Post body JSON if not None (POST),
                otherwise sends an empty payload (POST-as-GET).

        Returns:
            httpx.Response instance.

        Raises:
            AcmeError: in case of the error.
        """
        try:
            return await self._post_once(url, data)
        except AcmeBadNonceError:
            # Retry once
            logger.warning("POST retry on invalid nonce")
            return await self._post_once(url, data)

    async def _post_once(
        self: "AcmeClient", url: str, data: Optional[Dict[str, Any]]
    ) -> httpx.Response:
        """
        Perform a single HTTP POST request.

        Updates nonces if any responded.

        Args:
            url: Request URL
            data: Post body JSON if not None (POST),
                otherwise sends an empty payload (POST-as-GET).

        Returns:
            httpx.Response instance.

        Raises:
            AcmeConnectError: in case of transport errors.
            AcmeTimeoutError: on timeouts.
            AcmeBadNonceError: in case of bad nonce.
            AcmeError: in case of the error.
        """
        nonce = await self._get_nonce(url)
        logger.warning("POST %s", url)
        jws = self._to_jws(data, nonce=nonce, url=url)
        async with self._get_client() as client:
            try:
                resp = await self._wait_for(
                    client.post(
                        url,
                        content=jws,
                        headers={
                            "Content-Type": self.JOSE_CONTENT_TYPE,
                        },
                    ),
                    self._timeout,
                )
            except httpx.HTTPError as e:
                raise AcmeConnectError from e
            self._check_response(resp)
            self._nonce_from_response(resp)
            return resp

    async def _get_nonce(self: "AcmeClient", url: str) -> bytes:
        """
        Request new nonce.

        Request a new nonce from URL specified in directory
        or fallback to `url` parameter.

        Args:
            url: Fallback url in case the directory doesn't
                define a `newNonce` endpoint.

        Returns:
            nonce value as bytes.
        """
        if not self._nonces:
            d = await self._get_directory()
            nonce_url = url if d.new_nonce is None else d.new_nonce
            logger.warning("Fetching nonce from %s", nonce_url)
            resp = await self._head(nonce_url)
            self._check_response(resp)
        return self._nonces.pop()

    def _nonce_from_response(self: "AcmeClient", resp: httpx.Response) -> None:
        """
        Get nonce from response, if present.

        Fetches nonce from `Replay-Nonce` header.

        Args:
            resp: HTTP Response

        Raises:
            AcmeBadNonceError: on malformed nonce.
        """
        nonce = resp.headers.get(self.NONCE_HEADER)
        if nonce is None:
            return
        try:
            logger.warning("Registering new nonce %s", nonce)
            b_nonce = decode_b64jose(nonce)
            if b_nonce in self._nonces:
                msg = "Duplicated nonce"
                raise AcmeError(msg)
            self._nonces.add(b_nonce)
        except DeserializationError as e:
            logger.error("Bad nonce: %s", e)
            raise AcmeBadNonceError from e

    def _to_jws(
        self: "AcmeClient",
        data: Optional[Dict[str, Any]],
        *,
        nonce: Optional[bytes],
        url: str,
    ) -> str:
        """
        Convert a data to a signed JWS.

        Args:
            data: Dict of request data.
            nonce: Nonce to use.
            url: Requested url.

        Returns:
            Serialized signed JWS.
        """
        return AcmeJWS.sign(
            json.dumps(data, indent=2).encode() if data is not None else b"",
            alg=self._alg,
            nonce=nonce,
            url=url,
            key=self._key,
            kid=self._account_url,
        ).json_dumps(indent=2)

    @staticmethod
    def _check_response(resp: httpx.Response) -> None:
        """
        Check response and raise the errors when nessessary.

        Args:
            resp: Response instance

        Raises:
            AcmeUndecodableError: When failed to decode an error.
            AcmeBadNonceError: When the server rejects nonce.
            AcmeRateLimitError: When the server rejects the request
                due to high request rate.
        """
        if resp.status_code < BAD_REQUEST:
            return
        try:
            jdata = resp.json()
        except ValueError as e:
            raise AcmeUndecodableError from e
        e_type = jdata.get("type", "")
        if e_type == "urn:ietf:params:acme:error:badNonce":
            raise AcmeBadNonceError
        if e_type == "urn:ietf:params:acme:error:rateLimited":
            raise AcmeRateLimitError
        if e_type == "urn:ietf:params:acme:error:unauthorized":
            logger.error("Unauthorized: %s", jdata.get("detail", resp.text))
            raise AcmeUnauthorizedError
        e_detail = jdata.get("detail", "")
        msg = f"[{resp.status_code}] {e_type} {e_detail}"
        logger.error("Response error: %s", msg)
        raise AcmeError(msg)

    @staticmethod
    def get_key() -> JWKRSA:
        """
        Generate account key.

        Examples:
            ``` python
            key = AcmeClient.get_key()
            ```

        Returns:
            A key which can be used as `key` parameter
                to constructor.
        """
        logger.info("Generating new key")
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        return JWKRSA(key=private_key)

    async def fulfill_challenge(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Try to fulfill challege.

        Passes call to underlying `fulfill_*` function
        depending on the challenge type.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        if challenge.type == "http-01":
            h = self.fulfill_http_01
        elif challenge.type == "dns-01":
            h = self.fulfill_dns_01
        elif challenge.type == "tls-alpn-01":
            h = self.fulfill_tls_alpn_01
        else:
            return False
        logger.warning("Trying to fulfill %s for %s", challenge.type, domain)
        r = await h(domain, challenge)
        if r:
            logger.warning(
                "%s for %s is fulfilled successfully", challenge.type, domain
            )
        else:
            logger.warning("Skipping %s for %s", challenge.type, domain)
        return r

    async def fulfill_tls_alpn_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Fulfill the `tls-alpn-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_tls_alpn_01][gufo.acme.clients.base.AcmeClient.clear_tls_alpn_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def fulfill_http_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Fulfill the `http-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_http_01][gufo.acme.clients.base.AcmeClient.clear_http_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def fulfill_dns_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Fulfill the `dns-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_dns_01][gufo.acme.clients.base.AcmeClient.clear_dns_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def clear_challenge(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> None:
        """
        Clear up fulfillment after the challenge has been validated.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.
        """
        logger.warning(
            "Trying to clear challenge %s for %s", challenge.type, domain
        )
        if challenge.type == "http-01":
            return await self.clear_http_01(domain, challenge)
        if challenge.type == "dns-01":
            return await self.clear_dns_01(domain, challenge)
        if challenge.type == "tls-alpn-01":
            return await self.clear_tls_alpn_01(domain, challenge)
        return None

    async def clear_tls_alpn_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> None:
        """
        Clear up fulfillment after the `tls-alpn-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.
        """

    async def clear_http_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> None:
        """
        Clear up fulfillment after the `http-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.
        """

    async def clear_dns_01(
        self: "AcmeClient", domain: str, challenge: AcmeChallenge
    ) -> None:
        """
        Clear up fulfillment after the `dns-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: AcmeChallenge instance.
        """

    def get_key_authorization(
        self: "AcmeClient", challenge: AcmeChallenge
    ) -> bytes:
        """
        Calculate value for key authorization.

        According to RFC-8555 pp. 8.1.
        Should be used in `fulfill_*` functions.

        Args:
            challenge: ACME challenge.

        Returns:
            content of the key to be returned during challenge.
        """
        return "".join(
            [
                challenge.token,
                ".",
                encode_b64jose(self._key.thumbprint(hash_function=SHA256)),
            ]
        ).encode()

    @staticmethod
    def get_domain_private_key(key_size: int = 4096) -> bytes:
        """
        Generate private key for domain in PEM format.

        Args:
            key_size: RSA key size.

        Returns:
            Private key in PEM format.
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        return private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )

    @staticmethod
    def get_domain_csr(domain: str, private_key: bytes) -> bytes:
        """
        Generate CSR for domain in PEM format.

        Args:
            domain: Domain name.
            private_key: Private key in PEM format.
                `get_domain_private_key` may be used
                to generate one.

        Returns:
            CSR in PEM format.
        """
        # Read private key
        pk = cast(
            rsa.RSAPrivateKey,
            load_pem_private_key(private_key, password=None, backend=None),
        )
        # Generate CSR
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)])
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .sign(pk, algorithm=SHA256())
        )
        # Convert CSR to PEM format
        return csr.public_bytes(encoding=Encoding.PEM)

    def get_state(self: "AcmeClient") -> bytes:
        """
        Serialize the state of client to a stream of bytes.

        The state will contain all necessasy information
        to instantiate the new client by the
        `AcmeClient.from_state(...)`

        Return:
            State of the client as a stream of bytes
        """
        state = {
            "directory": self._directory_url,
            "key": self._key.fields_to_partial_json(),
        }
        if self._account_url is not None:
            state["account_url"] = self._account_url
        return json.dumps(state, indent=2).encode()

    @classmethod
    def from_state(cls: Type[CT], state: bytes, **kwargs: Any) -> CT:
        """
        Restore AcmeClient from the state.

        Restore the state of client from result of
        [AcmeClient.get_state][gufo.acme.clients.base.AcmeClient.get_state]
        call.

        Args:
            state: Stored state.
            kwargs: An additional arguments to be passed to constructor.

        Returns:
            New AcmeClient instance.
        """
        s = json.loads(state)
        return cls(
            s["directory"],
            key=JWKRSA.fields_from_json(s["key"]),
            account_url=s.get("account_url"),
            **kwargs,
        )
