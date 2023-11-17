# ---------------------------------------------------------------------
# CSR Proxy: DAVACMEClient client tests
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import asyncio
import os

import httpx

# Third-party modules
import pytest

# Gufo ACME modules
from gufo.acme.clients.base import ACMEClient
from gufo.acme.clients.dav import DAVACMEClient
from gufo.acme.error import ACMEFulfillmentFailed

from .utils import DIRECTORY, EMAIL, get_csr_pem, not_set, not_set_reason

ENV_CI_DAV_TEST_DOMAIN = "CI_DAV_TEST_DOMAIN"
ENV_CI_DAV_TEST_USER = "CI_DAV_TEST_USER"
ENV_CI_DAV_TEST_PASSWORD = "CI_DAV_TEST_PASSWORD"
SCENARIO_ENV = [
    ENV_CI_DAV_TEST_DOMAIN,
    ENV_CI_DAV_TEST_USER,
    ENV_CI_DAV_TEST_PASSWORD,
]


@pytest.mark.skipif(not_set(SCENARIO_ENV), reason=not_set_reason(SCENARIO_ENV))
def test_sign():
    async def inner():
        csr_pem = get_csr_pem(domain)
        #
        pk = DAVACMEClient.get_key()
        async with DAVACMEClient(
            DIRECTORY,
            username=os.getenv(ENV_CI_DAV_TEST_USER),
            password=os.getenv(ENV_CI_DAV_TEST_PASSWORD),
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

    domain = os.getenv(ENV_CI_DAV_TEST_DOMAIN) or ""
    asyncio.run(inner())


def test_state():
    client = ACMEClient(
        DIRECTORY,
        key=DAVACMEClient.get_key(),
    )
    state = client.get_state()
    client2 = DAVACMEClient.from_state(state, username="user", password="pass")
    assert isinstance(client2, DAVACMEClient)


def test_invalid_response():
    resp = httpx.Response(400)
    with pytest.raises(ACMEFulfillmentFailed):
        DAVACMEClient._check_dav_response(resp)
