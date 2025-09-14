# ---------------------------------------------------------------------
# CSR Proxy: ACMEv2 client tests
# ---------------------------------------------------------------------
# Copyright (C) 2023-25, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

# Third-party modules
import pytest
from josepy.jwk import JWKRSA

# Gufo ACME modules
from gufo.acme.clients.base import AcmeClient
from gufo.acme.error import (
    AcmeAlreadyRegistered,
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
from gufo.acme.types import AcmeChallenge, ExternalAccountBinding
from gufo.http import Response

from .utils import (
    EMAIL,
    GOOGLE_STAGE_DIRECTORY,
    KEY,
    LE_STAGE_DIRECTORY,
    ResponseStub,
    get_csr_pem,
    not_set,
    not_set_reason,
)

ENV_CI_ACME_TEST_DOMAIN = "CI_ACME_TEST_DOMAIN"
ENV_CI_GOOGLE_EAB_KID = "CI_GOOGLE_EAB_KID"
ENV_CI_GOOGLE_EAB_HMAC = "CI_GOOGLE_EAB_HMAC"


def test_get_directory() -> None:
    async def inner():
        async with AcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            d1 = await client._get_directory()
            assert d1.new_account
            # Cached
            d2 = await client._get_directory()
            assert d1 is d2

    asyncio.run(inner())


@pytest.mark.parametrize(
    ("directory", "expected"),
    [(LE_STAGE_DIRECTORY, False), (GOOGLE_STAGE_DIRECTORY, True)],
)
def test_external_account_required(directory: str, expected: bool) -> None:
    async def inner() -> bool:
        async with AcmeClient(directory, key=KEY) as client:
            d = await client._get_directory()
            return d.external_account_required

    r = asyncio.run(inner())
    assert r is expected


def test_get_nonce() -> None:
    async def inner():
        async with AcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            nonce = await client._get_nonce(LE_STAGE_DIRECTORY)
            assert nonce
            assert isinstance(nonce, bytes)

    asyncio.run(inner())


def test_to_jws() -> None:
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    nonce = b"12345"
    msg = client._to_jws(
        {
            "termsOfServiceAgreed": True,
            "contact": [
                "mailto:cert-admin@example.org",
                "mailto:admin@example.org",
            ],
        },
        nonce=nonce,
        url="1234",
    )
    msg_data = json.loads(msg)
    expected = {
        "protected": "eyJhbGciOiAiUlMyNTYiLCAiandrIjogeyJuIjogImd2dmpvSlBkMUw0c3ExYlQwcTJDOTROM1dWN1c3bHJvQV9NekYtU0dNVllGYXNJMmx2cXcza0FrRlJ4RzM2NkpmSHIzQjFSLXhsQ3pFUEhOaXhiTDZiMGNjdlBGWlpzdW5nbng1bV91R0wyRk1paXN1MTg2ZE1uZnNrNllzc3ZlYm94aVFYRWhHTXhJOVQ2R2pFNmw2ZWMxUEdZNXVCNzB2UDJ3a0dQeGt2UkxEMnRHYWVfLTdrQ2dSenZGMnhPYUdaalQtanhIY1lwV3V0Tk4tcVF6RG9IbmhMdTBMSXdXbFhCYXpBczZ6YmtQdlBXOVBOWkFVZW5jV3h4UTVoSnRMa1ZTdmdTWXd6STFjeGxyQzhsQ2pnNnJJUjlMQThzNVBMemVlX25Fb3RsamxVMGxqWHozZXlEOVc0Zmw0ckM0NnY4LXVmazVFejl1dFFRMnNWaklNUSIsICJlIjogIkFRQUIiLCAia3R5IjogIlJTQSJ9LCAibm9uY2UiOiAiTVRJek5EVSIsICJ1cmwiOiAiMTIzNCJ9",
        "signature": "b3TIXnHPaS7QymnJLk7NKBwpa3jbfD21h33ggQSX8FV4dj01y7zhhRY54BLceiHHYOEJg7z5fUECCSzSqdtSvHxMZXK14zNp9UOeLAkWavC7YKCyV2wxffcikbhhV_TyHxqyr2d0n5QHXX-L80yvKo61BgIv5PXRFnmi2eqhFI_j3zdwe7gpCjd2646hspnDxrclaxsv7xgleaXC3HDCVU0qYzVWCeC8FcmrLmXTWpzrO0oMCw2tDvYTx363aVtfPOVc6e7eIHlhUW-S9aUonSLAtfEQMxDgekxuVh1hG06GLSitgpdsYX97pmg6USGJidgRF8gGsOwribOFHaqy0Q",
        "payload": "ewogICJ0ZXJtc09mU2VydmljZUFncmVlZCI6IHRydWUsCiAgImNvbnRhY3QiOiBbCiAgICAibWFpbHRvOmNlcnQtYWRtaW5AZXhhbXBsZS5vcmciLAogICAgIm1haWx0bzphZG1pbkBleGFtcGxlLm9yZyIKICBdCn0",
    }
    assert msg_data == expected


def test_check_unbound():
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    client._check_unbound()
    with pytest.raises(AcmeNotRegistredError):
        client._check_bound()


def test_check_bound():
    client = AcmeClient(
        LE_STAGE_DIRECTORY, key=KEY, account_url="http://127.0.0.1/acc"
    )
    client._check_bound()
    with pytest.raises(AcmeAlreadyRegistered):
        client._check_unbound()


def test_new_and_deactivate_letsencrypt_account() -> None:
    async def inner():
        key = AcmeClient.get_key()
        async with AcmeClient(LE_STAGE_DIRECTORY, key=key) as client:
            client._check_unbound()
            uri = await client.new_account(EMAIL)
            assert uri is not None
            assert isinstance(uri, str)
            assert uri.startswith("http")
            client._check_bound()
            await client.deactivate_account()
            client._check_unbound()

    asyncio.run(inner())


@pytest.mark.skipif(
    not_set([ENV_CI_GOOGLE_EAB_KID, ENV_CI_GOOGLE_EAB_HMAC]),
    reason=not_set_reason([ENV_CI_GOOGLE_EAB_KID, ENV_CI_GOOGLE_EAB_HMAC]),
)
def test_new_and_deactivate_google_account() -> None:
    async def inner():
        key = AcmeClient.get_key()
        async with AcmeClient(GOOGLE_STAGE_DIRECTORY, key=key) as client:
            client._check_unbound()
            uri = await client.new_account(
                EMAIL,
                external_binding=ExternalAccountBinding(
                    kid=kid, hmac_key=hmac
                ),
            )
            assert uri is not None
            assert isinstance(uri, str)
            assert uri.startswith("http")
            client._check_bound()
            await client.deactivate_account()
            client._check_unbound()

    kid = os.getenv(ENV_CI_GOOGLE_EAB_KID) or ""
    hmac = AcmeClient.decode_auto_base64(
        os.getenv(ENV_CI_GOOGLE_EAB_HMAC) or ""
    )
    asyncio.run(inner())


def test_account_binding_required() -> None:
    async def inner() -> None:
        key = AcmeClient.get_key()
        async with AcmeClient(GOOGLE_STAGE_DIRECTORY, key=key) as client:
            with pytest.raises(AcmeExternalAccountRequred):
                await client.new_account(EMAIL)

    asyncio.run(inner())


def test_get_public_key() -> None:
    key = AcmeClient.get_key()
    assert key
    assert isinstance(key, JWKRSA)


def test_already_registered() -> None:
    async def inner():
        async with AcmeClient(
            LE_STAGE_DIRECTORY, key=KEY, account_url="http://127.0.0.1/"
        ) as client:
            with pytest.raises(AcmeAlreadyRegistered):
                await client.new_account(EMAIL)

    asyncio.run(inner())


class BlackholeHttpClient(object):
    """An http client that always timed out."""

    async def __aenter__(self: "BlackholeHttpClient") -> "BlackholeHttpClient":
        """Asynchronous context manager entry."""
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:
        """Asynchronous context manager exit."""

    async def _blackhole(self) -> None:
        await asyncio.sleep(100.0)

    async def get(self, url: str, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def head(self, url: str, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def post(self, url: str, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()


class BuggyHttpClient(object):
    """An http client that always raises ConnectError."""

    async def __aenter__(self) -> "BuggyHttpClient":
        """Asynchronous context manager entry."""
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> None:
        """Asynchronous context manager exit."""

    async def _blackhole(self):
        msg = "Connection failed"
        raise ConnectionError(msg)

    async def get(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def head(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def post(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()


class BlackholeAcmeClient(AcmeClient):
    DEFAULT_TIMEOUT = 0.0001

    def _get_client(self) -> BlackholeHttpClient:
        return BlackholeHttpClient()


class BlackholeAcmeClientBadNonce(BlackholeAcmeClient):
    async def _post_once(self, url: str, data: Dict[str, Any]) -> Response:
        raise AcmeBadNonceError()


class BuggyAcmeClient(AcmeClient):
    def _get_client(self) -> BuggyHttpClient:
        return BuggyHttpClient()


def test_get_directory_timeout():
    async def inner():
        async with BlackholeAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            with pytest.raises(AcmeTimeoutError):
                await client._get_directory()

    asyncio.run(inner())


def test_get_directory_error():
    async def inner():
        async with BuggyAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            with pytest.raises(AcmeConnectError):
                await client._get_directory()

    asyncio.run(inner())


def test_head_timeout():
    async def inner():
        async with BlackholeAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            with pytest.raises(AcmeTimeoutError):
                await client._head("")

    asyncio.run(inner())


def test_head_error():
    async def inner():
        async with BuggyAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            with pytest.raises(AcmeConnectError):
                await client._head("")

    asyncio.run(inner())


def test_post_timeout():
    async def inner():
        async with BlackholeAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(AcmeTimeoutError):
                await client._post("", {})

    asyncio.run(inner())


def test_post_error():
    async def inner():
        async with BuggyAcmeClient(LE_STAGE_DIRECTORY, key=KEY) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(AcmeConnectError):
                await client._post("", {})

    asyncio.run(inner())


def test_post_retry():
    async def inner():
        async with BlackholeAcmeClientBadNonce(
            LE_STAGE_DIRECTORY, key=KEY
        ) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(AcmeBadNonceError):
                await client._post("", {})

    asyncio.run(inner())


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("test@example.com", ["mailto:test@example.com"]),
        (
            ["test1@example.com", "test2@example.com"],
            ["mailto:test1@example.com", "mailto:test2@example.com"],
        ),
    ],
)
def test_email_to_contacts(
    email: Union[str, List[str]], expected: List[str]
) -> None:
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    r = client._email_to_contacts(email)
    assert r == expected


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ("example.com", [{"type": "dns", "value": "example.com"}]),
        (
            ["example.com", "sub.example.com"],
            [
                {"type": "dns", "value": "example.com"},
                {"type": "dns", "value": "sub.example.com"},
            ],
        ),
    ],
)
def test_domain_to_identifiers(
    domain: Union[str, List[str]], expected: List[str]
) -> None:
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    r = client._domain_to_identifiers(domain)
    assert r == expected


def test_check_response_err_no_json() -> None:
    resp = ResponseStub(status=400, content=b"foobar")
    with pytest.raises(AcmeUndecodableError):
        AcmeClient._check_response(resp)


@pytest.mark.parametrize(
    ("j", "etype"),
    [
        ({"type": "urn:ietf:params:acme:error:badNonce"}, AcmeBadNonceError),
        (
            {"type": "urn:ietf:params:acme:error:rateLimited"},
            AcmeRateLimitError,
        ),
        (
            {"type": "urn:ietf:params:acme:error:badSignatureAlgorithm"},
            AcmeError,
        ),
        (
            {"type": "urn:ietf:params:acme:error:unauthorized"},
            AcmeUnauthorizedError,
        ),
    ],
)
def test_check_response_err(j, etype):
    resp = ResponseStub(status=400, content=json.dumps(j).encode())
    with pytest.raises(etype):
        AcmeClient._check_response(resp)


def test_nonce_from_response():
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    assert not client._nonces
    resp = ResponseStub(
        status=200, headers={"Replay-Nonce": b"oFvnlFP1wIhRlYS2jTaXbA"}
    )
    client._nonce_from_response(resp)
    assert client._nonces == {
        b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
    }


def test_nonce_from_response_none():
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    assert not client._nonces
    resp = ResponseStub(status=200)
    client._nonce_from_response(resp)
    assert not client._nonces


def test_nonce_from_response_decode_error():
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    assert not client._nonces
    resp = ResponseStub(status=200, headers={"Replay-Nonce": b"x"})
    with pytest.raises(AcmeBadNonceError):
        client._nonce_from_response(resp)


def test_nonce_from_response_duplicated():
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    assert not client._nonces
    resp = ResponseStub(
        status=200, headers={"Replay-Nonce": b"oFvnlFP1wIhRlYS2jTaXbA"}
    )
    client._nonce_from_response(resp)
    with pytest.raises(AcmeError):
        client._nonce_from_response(resp)


TEST_CSR_PEM = b"""-----BEGIN CERTIFICATE REQUEST-----
MIIEZjCCAk4CAQAwITEfMB0GA1UEAwwWYWNtZS10ZXN0Lmd1Zm9sYWJzLmNvbTCC
AiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAL2m6C/w0+0tiIt3vTcHsQ5f
vCnCGFL4IpeqEOIs4EV6j/BCyQxv8SrplAsHZMjMD3w6xC4TIqBEWergWWPlBs1q
VviC2R9voCK6PrKc+F99dx+XIT5D16ZgSFTk1gkyBgVe91wZ2ldX5pxfTsb1Z0Qm
l+BpN27fUmrXPdY1Xd2YcEIbRdW5BEOau/zsdAbMTDBEhLsgIODM4aiTDiGyEWT1
br8PUnUnEpn+DEic1rucd+b7eBw30j3bgC33sSDkP1VxqV7ZFps2q05CHu2+2xuU
3mXa2eZjALelE7N7a6iTdUnBpERleWTCz8ZLMT5eTeahFGfrsJJSYm71fNqZBILz
Kt2Zx3anGkzHqkckM0j0okF9CXVXpwtV7FTXeoBghkGft9AnDVJQ7s9xJzfUg8fy
CP2rLSz0HeApXT2pUyGkIPgMEQOh4BfLZxOwqgQP+GcnQM+aepGpmWDXeIKp4O5z
HaLWn3FFzKzA4R1iz0hOxphDQVIVhwDdMY429zajHLtJfc3dVXFkTUUUSATN86AN
mlKWp9cmrrkFcc7EE03NAD94UptgXtPTFi4dWozsiB9QlO5p5fH77U/KLerFnF2F
rYCwpQo9bJLnFAklgo/QaSQH3J9MBuTPdsShvnM+4nDc1HK/maFR6qn6ls+agey9
5rSfdzJDbyMJ+b9RrPMZAgMBAAGgADANBgkqhkiG9w0BAQsFAAOCAgEAVXjmJU4f
PStiFeA9Kiko12IUeSY9fnLadEWpXmWe7NSE81D2SFyzD17Q9PcPwjvzs0oiQbJV
9psyuQin0DSQnvqJViIpdAljPalJ6t+kDxt3NXiHqVQaCyelWu8Z1+x4xtCdNZOd
ly7IkQ7beEBRPvIf4QBxXFY6ATRCN1k0p9RkGSaRXr9jaXqbSXWg+CiEDxUp0U4H
FUp08WyOHxYYymF0ojs5zD49+Vr9b5uvDJ+uIyqY5wc+qv3wFkCi/McyWb26SQJZ
3jcENHBjPNDxgxYcesoIiVXUam67kpDHf+hfj9bYq308wOaJSzTWco+q5TJx/YzG
icYDi7fbRgA6z/BBhxpzfQB/L2PVYPt5pi4wLLSi5xULyKj3TAAWmMvq8FIrZiiL
uAX5QkyEsiE86+A96xYDn8716OcHvNqwlqYxH5oYCxgXg2iorkXaGKvbN1aLkYwU
THMc4A2PYFsbHorJ9eDasckiNZJONsfz9Aj3gyCeqNio0nD1+29Dx3fg7MR0Ksmt
9rX4hKu9/575ffuScmMnKrHhtz5e/JEUc59EAjcY5sxIZ8NgW/Qpt5Ie1demsEi5
wuxaDRGWp1BtDD0N04nVl5dHPhE9+//Xvg7UmBLEg8EzZWz8kdYZm6iaQytVKcJk
j+5P0OacZ9fsw3GcrFs0LlHPLQ+sazO8kRg=
-----END CERTIFICATE REQUEST-----"""

TEST_CSR_DER = """
MIIEZjCCAk4CAQAwITEfMB0GA1UEAwwWYWNtZS10ZXN0Lmd1Zm9sYWJzLmNvbTCCAiIwDQYJ
KoZIhvcNAQEBBQADggIPADCCAgoCggIBAL2m6C/w0+0tiIt3vTcHsQ5fvCnCGFL4IpeqEOIs
4EV6j/BCyQxv8SrplAsHZMjMD3w6xC4TIqBEWergWWPlBs1qVviC2R9voCK6PrKc+F99dx+X
IT5D16ZgSFTk1gkyBgVe91wZ2ldX5pxfTsb1Z0Qml+BpN27fUmrXPdY1Xd2YcEIbRdW5BEOa
u/zsdAbMTDBEhLsgIODM4aiTDiGyEWT1br8PUnUnEpn+DEic1rucd+b7eBw30j3bgC33sSDk
P1VxqV7ZFps2q05CHu2+2xuU3mXa2eZjALelE7N7a6iTdUnBpERleWTCz8ZLMT5eTeahFGfr
sJJSYm71fNqZBILzKt2Zx3anGkzHqkckM0j0okF9CXVXpwtV7FTXeoBghkGft9AnDVJQ7s9x
JzfUg8fyCP2rLSz0HeApXT2pUyGkIPgMEQOh4BfLZxOwqgQP+GcnQM+aepGpmWDXeIKp4O5z
HaLWn3FFzKzA4R1iz0hOxphDQVIVhwDdMY429zajHLtJfc3dVXFkTUUUSATN86ANmlKWp9cm
rrkFcc7EE03NAD94UptgXtPTFi4dWozsiB9QlO5p5fH77U/KLerFnF2FrYCwpQo9bJLnFAkl
go/QaSQH3J9MBuTPdsShvnM+4nDc1HK/maFR6qn6ls+agey95rSfdzJDbyMJ+b9RrPMZAgMB
AAGgADANBgkqhkiG9w0BAQsFAAOCAgEAVXjmJU4fPStiFeA9Kiko12IUeSY9fnLadEWpXmWe
7NSE81D2SFyzD17Q9PcPwjvzs0oiQbJV9psyuQin0DSQnvqJViIpdAljPalJ6t+kDxt3NXiH
qVQaCyelWu8Z1+x4xtCdNZOdly7IkQ7beEBRPvIf4QBxXFY6ATRCN1k0p9RkGSaRXr9jaXqb
SXWg+CiEDxUp0U4HFUp08WyOHxYYymF0ojs5zD49+Vr9b5uvDJ+uIyqY5wc+qv3wFkCi/Mcy
Wb26SQJZ3jcENHBjPNDxgxYcesoIiVXUam67kpDHf+hfj9bYq308wOaJSzTWco+q5TJx/YzG
icYDi7fbRgA6z/BBhxpzfQB/L2PVYPt5pi4wLLSi5xULyKj3TAAWmMvq8FIrZiiLuAX5QkyE
siE86+A96xYDn8716OcHvNqwlqYxH5oYCxgXg2iorkXaGKvbN1aLkYwUTHMc4A2PYFsbHorJ
9eDasckiNZJONsfz9Aj3gyCeqNio0nD1+29Dx3fg7MR0Ksmt9rX4hKu9/575ffuScmMnKrHh
tz5e/JEUc59EAjcY5sxIZ8NgW/Qpt5Ie1demsEi5wuxaDRGWp1BtDD0N04nVl5dHPhE9+//X
vg7UmBLEg8EzZWz8kdYZm6iaQytVKcJkj+5P0OacZ9fsw3GcrFs0LlHPLQ+sazO8kRg="""


def test_pem_to_ber():
    der = AcmeClient._pem_to_der(TEST_CSR_PEM)
    expected = base64.b64decode(TEST_CSR_DER)
    assert der == expected


@pytest.mark.skipif(
    not_set([ENV_CI_ACME_TEST_DOMAIN]),
    reason=not_set_reason([ENV_CI_ACME_TEST_DOMAIN]),
)
def test_sign_no_fulfilment():
    async def inner():
        csr_pem = get_csr_pem(domain)
        pk = AcmeClient.get_key()
        async with AcmeClient(LE_STAGE_DIRECTORY, key=pk) as client:
            # Register account
            uri = await client.new_account(EMAIL)
            assert uri
            # Create new order
            with pytest.raises(AcmeFulfillmentFailed):
                await client.sign(domain, csr_pem)
            # Deactivate account
            await client.deactivate_account()

    domain = os.getenv(ENV_CI_ACME_TEST_DOMAIN) or ""
    asyncio.run(inner())


@pytest.mark.parametrize(
    "ch_type", ["http-01", "dns-01", "tls-alpn-01", "invalid"]
)
def test_default_fulfilment(ch_type: str) -> None:
    chall = AcmeChallenge(type=ch_type, url="", token="")
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    r = asyncio.run(client.fulfill_challenge("example.com", chall))
    assert r is False


@pytest.mark.parametrize(
    "ch_type", ["http-01", "dns-01", "tls-alpn-01", "invalid"]
)
def test_default_clear(ch_type: str) -> None:
    chall = AcmeChallenge(type=ch_type, url="", token="")
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    asyncio.run(client.clear_challenge("example.com", chall))


def test_get_csr() -> None:
    private_key = AcmeClient.get_domain_private_key()
    assert b"BEGIN RSA PRIVATE KEY" in private_key
    assert b"END RSA PRIVATE KEY" in private_key
    csr = AcmeClient.get_domain_csr("example.com", private_key)
    assert b"BEGIN CERTIFICATE REQUEST" in csr
    assert b"END CERTIFICATE REQUEST" in csr


def test_get_self_signed_certificate() -> None:
    private_key = AcmeClient.get_domain_private_key()
    assert b"BEGIN RSA PRIVATE KEY" in private_key
    assert b"END RSA PRIVATE KEY" in private_key
    csr = AcmeClient.get_domain_csr("example.com", private_key)
    assert b"BEGIN CERTIFICATE REQUEST" in csr
    assert b"END CERTIFICATE REQUEST" in csr
    cert = AcmeClient.get_self_signed_certificate(
        csr, private_key, validity_days=10
    )
    assert b"-BEGIN CERTIFICATE-" in cert
    assert b"-END CERTIFICATE-" in cert


def test_state1() -> None:
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    state = client.get_state()
    client2 = AcmeClient.from_state(state)
    assert client is not client2
    assert client._directory == client2._directory
    assert client._key == client2._key
    assert client2._account_url is None


def test_state2() -> None:
    client = AcmeClient(
        LE_STAGE_DIRECTORY, key=KEY, account_url="https://127.0.0.1/acc"
    )
    state = client.get_state()
    client2 = AcmeClient.from_state(state)
    assert client is not client2
    assert client._directory == client2._directory
    assert client._key == client2._key
    assert client._account_url == client2._account_url


def test_invalid_order_status() -> None:
    resp = ResponseStub(
        status=200, content=json.dumps({"status": "invalid"}).encode()
    )
    with pytest.raises(AcmeCertificateError):
        AcmeClient._get_order_status(resp)


def test_valid_order_status() -> None:
    resp = ResponseStub(
        status=200, content=json.dumps({"status": "valid"}).encode()
    )
    s = AcmeClient._get_order_status(resp)
    assert s == "valid"


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        (
            "0twaM-fK_6yfQ_rxH4eZdqj1O6blhB2",
            b"\xd2\xdc\x1a3\xe7\xca\xff\xac\x9fC\xfa\xf1\x1f\x87\x99v\xa8\xf5;\xa6\xe5\x84\x1d",
        ),
        (
            "0twaM+fK_6yfQ/rxH4eZdqj1O6blhB2",
            b"\xd2\xdc\x1a3\xe7\xca\xff\xac\x9fC\xfa\xf1\x1f\x87\x99v\xa8\xf5;\xa6\xe5\x84\x1d",
        ),
    ],
)
def test_decode_auto_base64(input: str, expected: bytes) -> None:
    r = AcmeClient.decode_auto_base64(input)
    assert r == expected


TEST_EAB_KID = "53271e20d46fc7462c1b615ef239e853"
TEST_EAB_HMAC = (
    "WA2XYh7UvKnG0twaM-fK_6yfQ_rxH4eZdqj1O6blhB2RIwyh3KjFDIrPyUZk"
    "ao5EyyPaUaYmk1Hl24LwgmqdEA"
)


def test_get_eab() -> None:
    client = AcmeClient(LE_STAGE_DIRECTORY, key=KEY)
    eab = client._get_eab(
        ExternalAccountBinding(
            kid=TEST_EAB_KID,
            hmac_key=AcmeClient.decode_auto_base64(TEST_EAB_HMAC),
        ),
        "http://127.0.0.1/new_account",
    )
    print(eab)
    assert eab == {
        "protected": "eyJhbGciOiAiSFMyNTYiLCAia2lkIjogIjUzMjcxZTIwZDQ2ZmM3NDYyYzFiNjE1ZWYyMzllODUzIiwgInVybCI6ICJodHRwOi8vMTI3LjAuMC4xL25ld19hY2NvdW50In0",
        "signature": "WdpEOa1e-Q9zyib7xzAFq3MrbUj82Gwt9RcLqqsr__Y",
        "payload": "eyJuIjogImd2dmpvSlBkMUw0c3ExYlQwcTJDOTROM1dWN1c3bHJvQV9NekYtU0dNVllGYXNJMmx2cXcza0FrRlJ4RzM2NkpmSHIzQjFSLXhsQ3pFUEhOaXhiTDZiMGNjdlBGWlpzdW5nbng1bV91R0wyRk1paXN1MTg2ZE1uZnNrNllzc3ZlYm94aVFYRWhHTXhJOVQ2R2pFNmw2ZWMxUEdZNXVCNzB2UDJ3a0dQeGt2UkxEMnRHYWVfLTdrQ2dSenZGMnhPYUdaalQtanhIY1lwV3V0Tk4tcVF6RG9IbmhMdTBMSXdXbFhCYXpBczZ6YmtQdlBXOVBOWkFVZW5jV3h4UTVoSnRMa1ZTdmdTWXd6STFjeGxyQzhsQ2pnNnJJUjlMQThzNVBMemVlX25Fb3RsamxVMGxqWHozZXlEOVc0Zmw0ckM0NnY4LXVmazVFejl1dFFRMnNWaklNUSIsICJlIjogIkFRQUIiLCAia3R5IjogIlJTQSJ9",
    }
