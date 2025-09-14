# ---------------------------------------------------------------------
# CSR Proxy: PowerDnsAcmeClient client tests
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import asyncio
import os

# Third-party modules
import pytest

# Gufo ACME modules
from gufo.acme.clients.base import AcmeClient
from gufo.acme.clients.powerdns import PowerDnsAcmeClient
from gufo.acme.error import AcmeFulfillmentFailed

from .utils import (
    EMAIL,
    LE_STAGE_DIRECTORY,
    ResponseStub,
    get_csr_pem,
    not_set,
    not_set_reason,
)

ENV_CI_POWERDNS_TEST_DOMAIN = "CI_POWERDNS_TEST_DOMAIN"
ENV_CI_POWERDNS_TEST_API_URL = "CI_POWERDNS_TEST_API_URL"
ENV_CI_POWERDNS_TEST_API_KEY = "CI_POWERDNS_TEST_API_KEY"
SCENARIO_ENV = [
    ENV_CI_POWERDNS_TEST_DOMAIN,
    ENV_CI_POWERDNS_TEST_API_URL,
    ENV_CI_POWERDNS_TEST_API_KEY,
]


@pytest.mark.skipif(not_set(SCENARIO_ENV), reason=not_set_reason(SCENARIO_ENV))
def test_sign():
    async def inner():
        csr_pem = get_csr_pem(domain)
        pk = PowerDnsAcmeClient.get_key()
        async with PowerDnsAcmeClient(
            LE_STAGE_DIRECTORY,
            api_url=os.getenv(ENV_CI_POWERDNS_TEST_API_URL),
            api_key=os.getenv(ENV_CI_POWERDNS_TEST_API_KEY),
            key=pk,
        ) as client:
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

    domain = os.getenv(ENV_CI_POWERDNS_TEST_DOMAIN) or ""
    asyncio.run(inner())


def test_state():
    client = AcmeClient(
        LE_STAGE_DIRECTORY,
        key=PowerDnsAcmeClient.get_key(),
    )
    state = client.get_state()
    client2 = PowerDnsAcmeClient.from_state(
        state, api_url="https://127.0.0.1/", api_key="xxx"
    )
    assert isinstance(client2, PowerDnsAcmeClient)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", "https://example.com"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_normalize_url(url: str, expected: str) -> None:
    r = PowerDnsAcmeClient._normalize_url(url)
    assert r == expected


def test_invalid_response():
    resp = ResponseStub(status=200)
    with pytest.raises(AcmeFulfillmentFailed):
        PowerDnsAcmeClient._check_api_response(resp)
