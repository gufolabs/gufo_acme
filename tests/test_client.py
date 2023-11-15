# ---------------------------------------------------------------------
# CSR Proxy: ACMEv2 client tests
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import asyncio
import base64
import json
import os
from typing import Any, Dict, List, Union

# Third-party modules
import httpx
import pytest

# CSR Proxy modules
from gufo.acme.client import ACMEClient
from gufo.acme.error import (
    ACMEAlreadyRegistered,
    ACMEBadNonceError,
    ACMEConnectError,
    ACMEError,
    ACMEFullfillmentFailed,
    ACMENotRegistredError,
    ACMERateLimitError,
    ACMETimeoutError,
    ACMEUnauthorizedError,
    ACMEUndecodableError,
)
from gufo.acme.types import ACMEChallenge
from httpx import ConnectError, Response

# Third-party modules
from josepy.jwk import JWKRSA

ENV_TEST_DOMAIN = "CI_TEST_DOMAIN"

EMAIL = "acme-000000000@gufolabs.com"
DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"
KEY = JWKRSA.from_json(
    {
        "n": "gvvjoJPd1L4sq1bT0q2C94N3WV7W7lroA_MzF-SGMVYFasI2lvqw3kAkFRxG366JfHr3B1R-xlCzEPHNixbL6b0ccvPFZZsungnx5m_uGL2FMiisu186dMnfsk6YssveboxiQXEhGMxI9T6GjE6l6ec1PGY5uB70vP2wkGPxkvRLD2tGae_-7kCgRzvF2xOaGZjT-jxHcYpWutNN-qQzDoHnhLu0LIwWlXBazAs6zbkPvPW9PNZAUencWxxQ5hJtLkVSvgSYwzI1cxlrC8lCjg6rIR9LA8s5PLzee_nEotljlU0ljXz3eyD9W4fl4rC46v8-ufk5Ez9utQQ2sVjIMQ",
        "e": "AQAB",
        "d": "AUosSQ5trbCn8VG1_R4D4y6oZiERwBf1bwUF9rUziFC01dLW3WSXaV_TryDHtqACBu-Rx0Di7O5aXgdIfycsv7bizOO3OM927XvS9cI6Q6R5l1do0IFA-smKVifRl3icDoX7uXHdCeDIkuAgTGlBl1iVSMyHotdMsP_1PS27wSb6q0miPLJzZFPcMz2WcRaPaVFjsg_l9J8_Sy6d0HWx7_2nrxvOESlUNwf7sRn2WY2ZQaGwBzS6L17aHeKkQiAgUMAJK6gF3SGLK8kiHJac-p5bxFMu38fFY3FcVCW-QJMhRZMHaV36XZliIfP6DLFBzHqj99iZqgR8LvQ1SeMLgQ",
        "p": "t8GsAuPj1WujpvId3eJwhPUsbxJuIcd0Zi6hLTlQvydOI4jUtfO9JzHvEFG9GSZtedaJ5Vga0OFQlpCyhNHLQe6JjJnriexazHK-dLlUr6cVmaCNSj9spa7azZF8ak8EtISAr-7zdzLGy2KiC-DsJwp36RlSOyD6APkDCthSoIE",
        "q": "tnrgWqyT2alj9gtjgWb-xY07qxFGBSBZEO6dY5hJsydbkLRGumX5mvhqKy3BBbROz1smVNlMxcJa8fEWwQn8EORmr9-86i6TQUyZyCRMbh1pO63D4mJGjuhCHDgKyzzxYczeBPI2MxFVnZHPUAjWJwUGZp3sMEGzwej5g0iwT7E",
        "dp": "jU8UVkylwlO6UAHU0fL2kGhyOSA1LSjS7FljfQGchMNXJaBt41aC2Ydezm_tOVAB1DYVaRbt2D_M11yCy_0Bj7w-bq9XIINv99UtfVmgNEwLIk8DGFvZ0ze572e4A5Csj51t0N2ywLF9ip5Y-0WGlSdJuynLwMjFOMZFfquILwE",
        "dq": "Ck1dpUDhCATcM-PotkGOWLDkkX_kKB3vaVlPYXQTlR2_uaez5oojUXB87fsjTqMjX-mRfHDYOMIESGyIEFXz-TAr6_oBvGbswV8Fv5rtBbp7Wncw-_L4cNEECnvPgDHsnszmK_lQvglYgBDfV3FoRcOu3NRFpWPQNj5k99h-u8E",
        "qi": "Z3Ipo4AnRJfszwEEb2Y-mZgkgrZJguoixPleH-QSmy9vJ17-9URMv62MWKv19X5HdluxZJYmKGSLbbuMWD9-MVntVFSb77YKNrE2kCGM8a--aWtv706dHUSZemRazib55HtcGn2H6D3laUigFSmPNCdfq8CjsWLeW8RVOyY5tgM",
        "kty": "RSA",
    }
)


def test_get_directory() -> None:
    async def inner():
        async with ACMEClient(DIRECTORY, key=KEY) as client:
            d1 = await client._get_directory()
            assert d1.new_account
            # Cached
            d2 = await client._get_directory()
            assert d1 is d2

    asyncio.run(inner())


def test_get_nonce() -> None:
    async def inner():
        async with ACMEClient(DIRECTORY, key=KEY) as client:
            nonce = await client._get_nonce(DIRECTORY)
            assert nonce
            assert isinstance(nonce, bytes)

    asyncio.run(inner())


def test_to_jws() -> None:
    client = ACMEClient(DIRECTORY, key=KEY)
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
    client = ACMEClient(DIRECTORY, key=KEY)
    client._check_unbound()
    with pytest.raises(ACMENotRegistredError):
        client._check_bound()


def test_check_bound():
    client = ACMEClient(DIRECTORY, key=KEY, account_url="http://127.0.0.1/acc")
    client._check_bound()
    with pytest.raises(ACMEAlreadyRegistered):
        client._check_unbound()


def test_new_and_deactivate_account() -> None:
    async def inner():
        key = ACMEClient.get_key()
        async with ACMEClient(DIRECTORY, key=key) as client:
            client._check_unbound()
            uri = await client.new_account(EMAIL)
            assert uri is not None
            assert isinstance(uri, str)
            assert uri.startswith("http")
            client._check_bound()
            await client.deactivate_account()
            client._check_unbound()

    asyncio.run(inner())


def test_get_public_key() -> None:
    key = ACMEClient.get_key()
    assert key
    assert isinstance(key, JWKRSA)


def test_already_registered() -> None:
    async def inner():
        async with ACMEClient(
            DIRECTORY, key=KEY, account_url="http://127.0.0.1/"
        ) as client:
            with pytest.raises(ACMEAlreadyRegistered):
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
        raise ConnectError(msg)

    async def get(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def head(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()

    async def post(self, url, *args, **kwargs: Dict[str, Any]):
        await self._blackhole()


class BlackholeACMEClient(ACMEClient):
    DEFAULT_TIMEOUT = 0.0001

    def _get_client(self) -> BlackholeHttpClient:
        return BlackholeHttpClient()


class BlackholeACMEClientBadNonce(BlackholeACMEClient):
    async def _post_once(self, url: str, data: Dict[str, Any]) -> Response:
        raise ACMEBadNonceError()


class BuggyACMEClient(ACMEClient):
    def _get_client(self) -> BuggyHttpClient:
        return BuggyHttpClient()


def test_get_directory_timeout():
    async def inner():
        async with BlackholeACMEClient(DIRECTORY, key=KEY) as client:
            with pytest.raises(ACMETimeoutError):
                await client._get_directory()

    asyncio.run(inner())


def test_get_directory_error():
    async def inner():
        async with BuggyACMEClient(DIRECTORY, key=KEY) as client:
            with pytest.raises(ACMEConnectError):
                await client._get_directory()

    asyncio.run(inner())


def test_head_timeout():
    async def inner():
        async with BlackholeACMEClient(DIRECTORY, key=KEY) as client:
            with pytest.raises(ACMETimeoutError):
                await client._head("")

    asyncio.run(inner())


def test_head_error():
    async def inner():
        async with BuggyACMEClient(DIRECTORY, key=KEY) as client:
            with pytest.raises(ACMEConnectError):
                await client._head("")

    asyncio.run(inner())


def test_post_timeout():
    async def inner():
        async with BlackholeACMEClient(DIRECTORY, key=KEY) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(ACMETimeoutError):
                await client._post("", {})

    asyncio.run(inner())


def test_post_error():
    async def inner():
        async with BuggyACMEClient(DIRECTORY, key=KEY) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(ACMEConnectError):
                await client._post("", {})

    asyncio.run(inner())


def test_post_retry():
    async def inner():
        async with BlackholeACMEClientBadNonce(DIRECTORY, key=KEY) as client:
            # Avoid HTTP call in get_nonce
            client._nonces.add(
                b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
            )
            with pytest.raises(ACMEBadNonceError):
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
    client = ACMEClient(DIRECTORY, key=KEY)
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
    client = ACMEClient(DIRECTORY, key=KEY)
    r = client._domain_to_identifiers(domain)
    assert r == expected


def test_check_response_err_no_json() -> None:
    resp = Response(400, text="foobar")
    with pytest.raises(ACMEUndecodableError):
        ACMEClient._check_response(resp)


@pytest.mark.parametrize(
    ("j", "etype"),
    [
        ({"type": "urn:ietf:params:acme:error:badNonce"}, ACMEBadNonceError),
        (
            {"type": "urn:ietf:params:acme:error:rateLimited"},
            ACMERateLimitError,
        ),
        (
            {"type": "urn:ietf:params:acme:error:badSignatureAlgorithm"},
            ACMEError,
        ),
        (
            {"type": "urn:ietf:params:acme:error:unauthorized"},
            ACMEUnauthorizedError,
        ),
    ],
)
def test_check_response_err(j, etype):
    resp = Response(400, json=j)
    with pytest.raises(etype):
        ACMEClient._check_response(resp)


def test_nonce_from_response():
    client = ACMEClient(DIRECTORY, key=KEY)
    assert not client._nonces
    resp = Response(200, headers={"Replay-Nonce": "oFvnlFP1wIhRlYS2jTaXbA"})
    client._nonce_from_response(resp)
    assert client._nonces == {
        b"\xa0[\xe7\x94S\xf5\xc0\x88Q\x95\x84\xb6\x8d6\x97l"
    }


def test_nonce_from_response_none():
    client = ACMEClient(DIRECTORY, key=KEY)
    assert not client._nonces
    resp = Response(200)
    client._nonce_from_response(resp)
    assert not client._nonces


def test_nonce_from_response_decode_error():
    client = ACMEClient(DIRECTORY, key=KEY)
    assert not client._nonces
    resp = Response(200, headers={"Replay-Nonce": "x"})
    with pytest.raises(ACMEBadNonceError):
        client._nonce_from_response(resp)


def test_nonce_from_response_duplicated():
    client = ACMEClient(DIRECTORY, key=KEY)
    assert not client._nonces
    resp = Response(200, headers={"Replay-Nonce": "oFvnlFP1wIhRlYS2jTaXbA"})
    client._nonce_from_response(resp)
    with pytest.raises(ACMEError):
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
    der = ACMEClient._pem_to_der(TEST_CSR_PEM)
    expected = base64.b64decode(TEST_CSR_DER)
    assert der == expected


class ACMESigner(ACMEClient):
    async def fulfill_http_01(
        self, domain: str, challenge: ACMEChallenge
    ) -> bool:
        """Upload challenge."""
        async with self._get_client() as client:
            domain = os.getenv(ENV_CI_ACME_TEST_DOMAIN) or ""
            v = self.get_key_authorization(challenge)
            resp = await client.put(
                f"http://{domain}/.well-known/acme-challenge/{challenge.token}",
                content=v,
                auth=httpx.BasicAuth(
                    username=os.getenv(ENV_CI_ACME_TEST_USER),
                    password=os.getenv(ENV_CI_ACME_TEST_USERKEY),
                ),
            )
            if resp.status_code > 299:
                msg = f"Failed to put challenge: code {resp.status_code}"
                raise ACMEError(msg)
        return True

    async def clear_http_01(
        self: ACMEClient, domain: str, challenge: ACMEChallenge
    ) -> None:
        async with self._get_client() as client:
            domain = os.getenv(ENV_CI_ACME_TEST_DOMAIN) or ""
            resp = await client.delete(
                f"http://{domain}/.well-known/acme-challenge/{challenge.token}",
                auth=httpx.BasicAuth(
                    username=os.getenv(ENV_CI_ACME_TEST_USER),
                    password=os.getenv(ENV_CI_ACME_TEST_USERKEY),
                ),
            )
            if resp.status_code > 299:
                msg = f"Failed to put challenge: code {resp.status_code}"
                raise ACMEError(msg)


def get_csr_pem(domain: str) -> bytes:
    """Generate CSR for domain in PEM format."""
    private_key = ACMEClient.get_domain_private_key()
    return ACMEClient.get_domain_csr(domain, private_key)


ENV_CI_ACME_TEST_DOMAIN = "CI_ACME_TEST_DOMAIN"
ENV_CI_ACME_TEST_USER = "CI_ACME_TEST_USER"
ENV_CI_ACME_TEST_USERKEY = "CI_ACME_TEST_PASS"


def to_skip_scenario() -> bool:
    return not (
        os.environ.get(ENV_CI_ACME_TEST_DOMAIN)
        and os.environ.get(ENV_CI_ACME_TEST_USER)
        and os.environ.get(ENV_CI_ACME_TEST_USERKEY)
    )


@pytest.mark.skipif(
    to_skip_scenario(),
    reason=f"{ENV_CI_ACME_TEST_DOMAIN}, {ENV_CI_ACME_TEST_USER}, {ENV_CI_ACME_TEST_USERKEY}"
    " variables must be set",
)
def test_sign():
    async def inner():
        csr_pem = get_csr_pem(domain)
        #
        pk = ACMEClient.get_key()
        async with ACMESigner(DIRECTORY, key=pk) as client:
            # Register account
            uri = await client.new_account(EMAIL)
            assert uri
            # Create new order
            cert = await client.sign(domain, csr_pem)
            # Deactivate account
            await client.deactivate_account()
        assert cert
        assert b"BEGIN CERTIFICATE" in cert
        assert b"END CERTIFICATE" in cert

    domain = os.getenv(ENV_CI_ACME_TEST_DOMAIN) or ""
    asyncio.run(inner())


@pytest.mark.skipif(
    to_skip_scenario(),
    reason=f"{ENV_CI_ACME_TEST_DOMAIN}, {ENV_CI_ACME_TEST_USER}, {ENV_CI_ACME_TEST_USERKEY}"
    " variables must be set",
)
def test_sign_no_fullfilment():
    async def inner():
        csr_pem = get_csr_pem(domain)
        #
        pk = ACMEClient.get_key()
        async with ACMEClient(DIRECTORY, key=pk) as client:
            # Register account
            uri = await client.new_account(EMAIL)
            assert uri
            # Create new order
            with pytest.raises(ACMEFullfillmentFailed):
                await client.sign(domain, csr_pem)
            # Deactivate account
            await client.deactivate_account()

    domain = os.getenv(ENV_CI_ACME_TEST_DOMAIN) or ""
    asyncio.run(inner())


@pytest.mark.parametrize(
    "ch_type", ["http-01", "dns-01", "tls-alpn-01", "invalid"]
)
def test_default_fullfilment(ch_type: str) -> None:
    chall = ACMEChallenge(type=ch_type, url="", token="")
    client = ACMEClient(DIRECTORY, key=KEY)
    r = asyncio.run(client.fulfill_challenge("example.com", chall))
    assert r is False


@pytest.mark.parametrize(
    "ch_type", ["http-01", "dns-01", "tls-alpn-01", "invalid"]
)
def test_default_clear(ch_type: str) -> None:
    chall = ACMEChallenge(type=ch_type, url="", token="")
    client = ACMEClient(DIRECTORY, key=KEY)
    asyncio.run(client.clear_challenge("example.com", chall))


def test_get_csr() -> None:
    private_key = ACMEClient.get_domain_private_key()
    assert b"BEGIN RSA PRIVATE KEY" in private_key
    assert b"END RSA PRIVATE KEY" in private_key
    csr = ACMEClient.get_domain_csr("example.com", private_key)
    assert b"BEGIN CERTIFICATE REQUEST" in csr
    assert b"END CERTIFICATE REQUEST" in csr


def test_state1() -> None:
    client = ACMEClient(DIRECTORY, key=KEY)
    state = client.get_state()
    client2 = ACMEClient.from_state(state)
    assert client is not client2
    assert client._directory == client2._directory
    assert client._key == client2._key
    assert client2._account_url is None


def test_state2() -> None:
    client = ACMEClient(
        DIRECTORY, key=KEY, account_url="https://127.0.0.1/acc"
    )
    state = client.get_state()
    client2 = ACMEClient.from_state(state)
    assert client is not client2
    assert client._directory == client2._directory
    assert client._key == client2._key
    assert client._account_url == client2._account_url
