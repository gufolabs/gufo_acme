# ---------------------------------------------------------------------
# Gufo ACME: ACMEClient implementation
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""An ACMEClient implementation."""
# Python modules
import asyncio
import json
import random
from types import TracebackType
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    Union,
)

# Third-party modules
import httpx
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding
from josepy.errors import DeserializationError
from josepy.json_util import decode_b64jose, encode_b64jose
from josepy.jwa import RS256, JWASignature
from josepy.jwk import JWK, JWKRSA

# Gufo ACME modules
from . import __version__
from .acme import AcmeJWS
from .error import (
    ACMEAlreadyRegistered,
    ACMEAuthorizationError,
    ACMEBadNonceError,
    ACMECertificateError,
    ACMEConnectError,
    ACMEError,
    ACMEFullfillmentFailed,
    ACMENotRegistredError,
    ACMERateLimitError,
    ACMETimeoutError,
    ACMEUnauthorizedError,
    ACMEUndecodableError,
)
from .log import logger
from .types import ACMEAuthorization, ACMEChallenge, ACMEDirectory, ACMEOrder

BAD_REQUEST = 400


class ACMEClient(object):
    """
    ACME Client.

    Examples:
    Create new account:
    ``` python
    async with ACMEClient(directory, key=key) as client:
        uri = await client.new_account("test@example.com")
    ```
    Sign an CSR:
    ``` python
    class SignClient(ACMEClient):
        async def fulfill_http_01(
            self, domain: str, challenge: ACMEChallenge
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
            by the [gufo.acme.client.ACMEClient.get_key][] function.
        alg: Signing algorithm to use.
        account_url: Optional ACME account URL, cotaining the
            stored result of the previous call to the
            [gufo.acme.client.ACMEClient.new_account][] function.
        timeout: Network requests timeout in seconds.
        user_agent: Override default User-Agent header.
    """

    JOSE_CONTENT_TYPE: str = "application/jose+json"
    NONCE_HEADER: str = "Replay-Nonce"
    RETRY_AFTER_HEADER: str = "Retry-After"
    DEFAULT_TIMEOUT: float = 40.0

    def __init__(
        self: "ACMEClient",
        directory_url: str,
        *,
        key: JWK,
        alg: JWASignature = RS256,
        account_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.directory_url = directory_url
        self.directory_lock = asyncio.Lock()
        self.directory: Optional[ACMEDirectory] = None
        self.key = key
        self.alg = alg
        self.account_url = account_url
        self.nonces: Set[bytes] = set()
        self.nonce_lock = asyncio.Lock()
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.user_agent = user_agent or f"Gufo ACME/{__version__}"

    async def __aenter__(self: "ACMEClient") -> "ACMEClient":
        """
        An asynchronous context manager.

        Examples:
            ``` py
            async with ACMEClient(....) as client:
                ...
            ```
        """
        return self

    async def __aexit__(
        self: "ACMEClient",
        exc_t: Optional[Type[BaseException]],
        exc_v: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Asynchronous context exit."""
        return

    def is_bound(self: "ACMEClient") -> bool:
        """
        Check if the client is bound to the account.

        The client may be bound to account either:

        * By setting `account_url` in constructor.
        * By calling [gufo.acme.client.ACMEClient.new_account][]

        Returns:
            True - if the client is bound to account,
                False - otherwise.
        """
        return self.account_url is not None

    def _check_bound(self: "ACMEClient") -> None:
        """
        Check the client is bound to account.

        Raises:
            ACMENotRegistredError: if client is not bound.
        """
        if not self.is_bound():
            raise ACMENotRegistredError

    def _check_unbound(self: "ACMEClient") -> None:
        """
        Check the client is not  bound to account.

        Raises:
            ACMEAlreadyRegistered: if client is bound.
        """
        if self.is_bound():
            raise ACMEAlreadyRegistered

    def _get_client(self: "ACMEClient") -> httpx.AsyncClient:
        """
        Get a HTTP client instance.

        May be overrided in subclasses to configure
        or replace httpx.AsyncClient.

        Returns:
            Async HTTP client instance.
        """
        return httpx.AsyncClient(
            http2=True, headers={"User-Agent": self.user_agent}
        )

    async def _get_directory(self: "ACMEClient") -> ACMEDirectory:
        """
        Get and ACME directory.

        Caches response to fetch request only once.

        Returns:
            ACMEDirectory instance containing URLs
            for ACME server.

        Raises:
            ACMEError: In case of the errors.
        """
        async with self.directory_lock:
            if self.directory is not None:
                return self.directory
            async with self._get_client() as client:
                logger.warning(
                    "Fetching ACME directory from %s", self.directory_url
                )
                try:
                    r = await asyncio.wait_for(
                        client.get(self.directory_url), self.timeout
                    )
                except asyncio.TimeoutError as e:
                    raise ACMETimeoutError from e
                except httpx.HTTPError as e:
                    raise ACMEConnectError from e
                self._check_response(r)
                data = r.json()
            self.directory = ACMEDirectory(
                new_account=data["newAccount"],
                new_nonce=data.get("newNonce"),
                new_order=data["newOrder"],
            )
            return self.directory

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

    async def new_account(
        self: "ACMEClient", email: Union[str, Iterable[str]]
    ) -> str:
        """
        Create new account.

        Performs RFC-8555 pp. 7.3 call to create new account.
        The account will be bind to the used key.

        Examples:
            Create an account with single contact email:

            ``` python
            async with ACMEClient(directory, key=key) as client:
                uri = await client.new_account("test@example.com")
            ```

            Create an account with multiple contact emails:

            ``` python
            async with ACMEClient(directory, key=key) as client:
                uri = await client.new_account([
                    "ca@example.com",
                    "boss@example.com"
                ])
            ```

        Args:
            email: String containing email or any iterable yielding emails.

        Returns:
            ACME account url which can be passed as `account_url` parameter
                to the ACME client.

        Raises:
            ACMEError: In case of the errors.
            ACMEAlreadyRegistered: If an client is already bound to account.
        """
        # Build contacts
        contacts = self._email_to_contacts(email)
        logger.warning("Creating new account: %s", ", ".join(contacts))
        # Check the client is not already bound
        self._check_unbound()
        # Refresh directory
        d = await self._get_directory()
        # Post request
        resp = await self._post(
            d.new_account,
            {
                "termsOfServiceAgreed": True,
                "contact": contacts,
            },
        )
        self.account_url = resp.headers["Location"]
        return self.account_url

    async def deactivate_account(self: "ACMEClient") -> None:
        """
        Deactivate account.

        Performs RFC-8555 pp. 7.3.6 call to deactivate an account.
        A deactivated account can no longer request certificate
        issuance or access resources related to the account,
        such as orders or authorizations.

        To call `deactivate_account` ACMEClient must be bound
        to acount either via `account_url` option or
        via `new_account` call. After successfully processing
        a client will be unbound from account.

        Examples:
            Deactivate account:

            ``` python
            async with ACMEClient(
                directory, key=key,
                account_url=url
            ) as client:
                uri = await client.deactivate_account()
            ```

        Raises:
            ACMEError: In case of the errors.
            ACMENotRegistred: If the client is not bound to account.
        """
        logger.warning("Deactivating account: %s", self.account_url)
        # Check account is really bound
        self._check_bound()
        # Send deactivation request
        await self._post(
            self.account_url,  # type: ignore
            {"status": "deactivated"},
        )
        # Unbind client
        self.account_url = None

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
        self: "ACMEClient", domain: Union[str, Iterable[str]]
    ) -> ACMEOrder:
        """
        Create new order.

        Performs RFC-8555 pp. 7.4 order creation sequence.
        Before creating a new order any of the prerequisites must be met.

        * `new_accout()` function called.
        * `account_url` passed to constructor.

        Examples:
            Order for single domain:

            ``` python
            async with ACMEClient(
                directory,
                key=key,
                account_url=account_url
            ) as client:
                order = await client.new_order("example.com")
            ```

            Order for multiple domains:

            ``` py
            async with ACMEClient(
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
            An ACMEOrder object.

        Raises:
            ACMEError: In case of the errors.
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
        return ACMEOrder(
            authorizations=[
                ACMEAuthorization(domain=i["value"], url=a)
                for i, a in zip(identifiers, data["authorizations"])
            ],
            finalize=data["finalize"],
        )

    async def get_challenges(
        self: "ACMEClient", auth: ACMEAuthorization
    ) -> List[ACMEChallenge]:
        """
        Get a challenge for an authoriations.

        Performs RFC-8555 pp. 7.5 sequence.

        Examples:
            ``` python
            async with ACMEClient(
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
            auth: ACMEAuthorization object, usually from
                ACMEOrder.authorizations.

        Returns:
            List of ACMEChallenge.

        Raises:
            ACMEError: In case of the errors.
        """
        logger.warning("Getting challenges for %s", auth.domain)
        self._check_bound()
        resp = await self._post(auth.url, None)
        data = resp.json()
        return [
            ACMEChallenge(type=d["type"], url=d["url"], token=d["token"])
            for d in data["challenges"]
        ]

    async def respond_challenge(
        self: "ACMEClient", challenge: ACMEChallenge
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
        self: "ACMEClient", auth: ACMEAuthorization
    ) -> None:
        """
        Wait untill authorization became valid.

        Args:
            auth: ACME Authorization
        """
        for _ in range(10):  # @todo: Replace with timeout
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
                raise ACMEAuthorizationError(msg)
        msg = "Too many polls"
        raise ACMEAuthorizationError(msg)

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

    async def finalize_and_wait(
        self: "ACMEClient", order: ACMEOrder, *, csr: bytes
    ) -> str:
        """
        Send finalization request and wait for the certificate.

        Args:
            order: ACME Order.
            csr: CSR in PEM format.

        Returns:
            Signed certificate in PEM format.

        Raises:
            ACMECertificateError: When server refuses
                to sign the certificate.
        """
        logger.warning("Finalizing order")
        self._check_bound()
        resp = await self._post(
            order.finalize, {"csr": encode_b64jose(self._pem_to_der(csr))}
        )
        data = resp.json()
        status = data["status"]
        if status == "invalid":
            msg = "Failed to finalize order"
            raise ACMECertificateError(msg)
        order_uri = resp.headers["Location"]
        # Poll for certificate
        await self._random_delay(1.0)
        while True:
            logger.warning("Polling order")
            resp = await self._post(order_uri, None)
            data = resp.json()
            status = data["status"]
            if status == "invalid":
                msg = "Failed to finalize order"
                raise ACMECertificateError(msg)
            if status == "valid":
                logger.warning("Order is ready. Downloading certificate")
                resp = await self._post(data["certificate"], None)
                return resp.text

    async def sign(self: "ACMEClient", domain: str, csr: bytes) -> str:
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
            class SignClient(ACMEClient):
                async def fulfill_http_01(
                    self, domain: str, challenge: ACMEChallenge
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
            ACMETimeoutError: On timeouts.
            ACMEFullfillmentFailed: If the client failed to
                fulfill any challenge.
            ACMEError: and subclasses in case of other errors.
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
                raise ACMEFullfillmentFailed
            # Wait for authorization became valid
            try:
                await asyncio.wait_for(self.wait_for_authorization(auth), 60.0)
            except asyncio.TimeoutError as e:
                raise ACMETimeoutError from e
            # Clear challenge
            await self.clear_challenge(domain, fulfilled_challenge)
        # Finalize order and get certificate
        try:
            return await asyncio.wait_for(
                self.finalize_and_wait(order, csr=csr), 60.0
            )
        except asyncio.TimeoutError as e:
            raise ACMETimeoutError from e

    async def _head(self: "ACMEClient", url: str) -> httpx.Response:
        """
        Perform HTTP HEAD request.

        Performs HTTP HEAD request using underlied HTTP client.
        Updates nonces if any responded.

        Args:
            url: Request URL

        Returns:
            httpx.Response instance.

        Raises:
            ACMEError: in case of error.
        """
        logger.warning("HEAD %s", url)
        async with self._get_client() as client:
            try:
                r = await asyncio.wait_for(
                    client.head(url),
                    self.timeout,
                )
            except asyncio.TimeoutError as e:
                raise ACMETimeoutError from e
            except httpx.HTTPError as e:
                raise ACMEConnectError from e
            self._check_response(r)
            self._nonce_from_response(r)
            return r

    async def _post(
        self: "ACMEClient", url: str, data: Optional[Dict[str, Any]]
    ) -> httpx.Response:
        """
        Perform HTTP POST request.

        Performs HTTP POST request using underlied HTTP client.
        Updates nonces if any responded. Retries once
        if the nonce was rejected by server.
        Raises an ACMEError in case of the error.

        Args:
            url: Request URL
            data: Post body JSON if not None (POST),
                otherwise sends an empty payload (POST-as-GET).

        Returns:
            httpx.Response instance.

        Raises:
            ACMEError: in case of the error.
        """
        try:
            return await self._post_once(url, data)
        except ACMEBadNonceError:
            # Retry once
            logger.warning("POST retry on invalid nonce")
            return await self._post_once(url, data)

    async def _post_once(
        self: "ACMEClient", url: str, data: Optional[Dict[str, Any]]
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
            ACMEConnectError: in case of transport errors.
            ACMETimeoutError: on timeouts.
            ACMEBadNonceError: in case of bad nonce.
            ACMEError: in case of the error.
        """
        logger.warning("POST %s", url)
        nonce = await self._get_nonce(url)
        jws = self._to_jws(data, nonce=nonce, url=url)
        async with self._get_client() as client:
            try:
                resp = await asyncio.wait_for(
                    client.post(
                        url,
                        content=jws,
                        headers={
                            "Content-Type": self.JOSE_CONTENT_TYPE,
                        },
                    ),
                    self.timeout,
                )
            except asyncio.TimeoutError as e:
                raise ACMETimeoutError from e
            except httpx.HTTPError as e:
                raise ACMEConnectError from e
            self._check_response(resp)
            self._nonce_from_response(resp)
            return resp

    async def _get_nonce(self: "ACMEClient", url: str) -> bytes:
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
        if not self.nonces:
            d = await self._get_directory()
            nonce_url = url if d.new_nonce is None else d.new_nonce
            logger.warning("Fetching nonce from %s", nonce_url)
            resp = await self._head(nonce_url)
            self._check_response(resp)
        return self.nonces.pop()

    def _nonce_from_response(self: "ACMEClient", resp: httpx.Response) -> None:
        """
        Get nonce from response, if present.

        Fetches nonce from `Replay-Nonce` header.

        Args:
            resp: HTTP Response

        Raises:
            ACMEBadNonceError: on malformed nonce.
        """
        nonce = resp.headers.get(self.NONCE_HEADER)
        if nonce is None:
            return
        try:
            logger.warning("Registering new nonce %s", nonce)
            b_nonce = decode_b64jose(nonce)
            if b_nonce in self.nonces:
                msg = "Duplicated nonce"
                raise ACMEError(msg)
            self.nonces.add(b_nonce)
        except DeserializationError as e:
            logger.error("Bad nonce: %s", e)
            raise ACMEBadNonceError from e

    def _to_jws(
        self: "ACMEClient",
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
            alg=self.alg,
            nonce=nonce,
            url=url,
            key=self.key,
            kid=self.account_url,
        ).json_dumps(indent=2)

    @staticmethod
    def _check_response(resp: httpx.Response) -> None:
        """
        Check response and raise the errors when nessessary.

        Args:
            resp: Response instance

        Raises:
            ACMEUndecodableError: When failed to decode an error.
            ACMEBadNonceError: When the server rejects nonce.
            ACMERateLimitError: When the server rejects the request
                due to high request rate.
        """
        if resp.status_code < BAD_REQUEST:
            return
        try:
            jdata = resp.json()
        except ValueError as e:
            raise ACMEUndecodableError from e
        e_type = jdata.get("type", "")
        if e_type == "urn:ietf:params:acme:error:badNonce":
            raise ACMEBadNonceError
        if e_type == "urn:ietf:params:acme:error:rateLimited":
            raise ACMERateLimitError
        if e_type == "urn:ietf:params:acme:error:unauthorized":
            raise ACMEUnauthorizedError
        e_detail = jdata.get("detail", "")
        msg = f"[{resp.status_code}] {e_type} {e_detail}"
        logger.error("Response error: %s", msg)
        raise ACMEError(msg)

    @staticmethod
    def get_key() -> JWKRSA:
        """
        Generate account key.

        Examples:
            ``` python
            key = ACMEClient.get_key()
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
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> bool:
        """
        Try to fulfill challege.

        Passes call to underlying `fulfill_*` function
        depending on the challenge type.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.

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
        logger.warning("Trying to fullfill %s for %s", challenge.type, domain)
        r = await h(domain, challenge)
        if r:
            logger.warning(
                "%s for %s is fulfilled successfully", challenge.type, domain
            )
        else:
            logger.warning("Skipping %s for %s", challenge.type, domain)
        return r

    async def fulfill_tls_alpn_01(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> bool:
        """
        Fulfill the `tls-alpn-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_tls_alpn_01][gufo.acme.client.ACMEClient.clear_tls_alpn_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def fulfill_http_01(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> bool:
        """
        Fulfill the `http-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_http_01][gufo.acme.client.ACMEClient.clear_http_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def fulfill_dns_01(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> bool:
        """
        Fulfill the `dns-01` type of challenge.

        Should be overriden in subclasses to perform all
        necessary jobs. Override
        [clear_dns_01][gufo.acme.client.ACMEClient.clear_dns_01]
        to perform cleanup.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.

        Returns:
            True: if the challenge is fulfilled.
            False: when failed to fulfill the challenge.
        """
        return False

    async def clear_challenge(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> None:
        """
        Clear up fulfillment after the challenge has been validated.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.
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
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> None:
        """
        Clear up fulfillment after the `tls-alpn-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.
        """

    async def clear_http_01(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> None:
        """
        Clear up fulfillment after the `http-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.
        """

    async def clear_dns_01(
        self: "ACMEClient", domain: str, challenge: ACMEChallenge
    ) -> None:
        """
        Clear up fulfillment after the `dns-01` has been validated.

        Should be overriden in the subclasses to perform the real job.

        Args:
            domain: Domain name.
            challenge: ACMEChallenge instance.
        """

    def get_key_authorization(
        self: "ACMEClient", challenge: ACMEChallenge
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
                encode_b64jose(self.key.thumbprint(hash_function=SHA256)),
            ]
        ).encode()
