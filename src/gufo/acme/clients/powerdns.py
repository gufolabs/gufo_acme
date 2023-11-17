# ---------------------------------------------------------------------
# Gufo ACME: PowerDnsAcmeClient implementation
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""A PowerDnsAcmeClient implementation."""

# Python modules
import hashlib
from typing import Any

import httpx

# Third-party modules
from josepy.json_util import encode_b64jose

# Gufo ACME modules
from ..error import AcmeFulfillmentFailed
from ..log import logger
from ..types import AcmeChallenge
from .base import AcmeClient

RESP_NO_CONTENT = 204


class PowerDnsAcmeClient(AcmeClient):
    """
    PowerDNS compatible ACME Client.

    Fulfills dns-01 challenge by manipulating
    DNS RR via PowerDNS API.

    Args:
        api_url: Root url of the PowerDNS web.
        api_key: PowerDNS API key.
    """

    def __init__(
        self: "PowerDnsAcmeClient",
        directory_url: str,
        *,
        api_url: str,
        api_key: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(directory_url, **kwargs)
        self.api_url = self._normalize_url(api_url)
        self.api_key = api_key

    @staticmethod
    def _normalize_url(url: str) -> str:
        if url.endswith("/"):
            return url[:-1]
        return url

    @staticmethod
    def _check_api_response(resp: httpx.Response) -> None:
        if resp.status_code != RESP_NO_CONTENT:
            msg = f"Failed to fulfill: Server returned {resp}"
            logger.error(msg)
            raise AcmeFulfillmentFailed(msg)

    async def fulfill_dns_01(
        self: "PowerDnsAcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Fulfill dns-01 challenge.

        Update token via PowerDNS API.

        Args:
            domain: Domain name
            challenge: AcmeChallenge instance, containing token.

        Returns:
            True - on succeess.

        Raises:
            AcmeFulfillmentFailed: On error.
        """
        # Calculate value
        v = encode_b64jose(
            hashlib.sha256(self.get_key_authorization(challenge)).digest()
        )
        # Set PDNS challenge
        async with self._get_client() as client:
            # Construct the API endpoint for updating
            # a record in a specific zone
            endpoint = (
                f"{self.api_url}/api/v1/servers/localhost/zones/{domain}"
            )
            # Set up the headers, including the API key for authentication
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            }
            # Prepare the payload for the update
            update_payload = {
                "rrsets": [
                    {
                        "name": f"_acme-challenge.{domain}.",
                        "type": "TXT",
                        "ttl": 1,
                        "changetype": "REPLACE",
                        "records": [
                            {
                                "content": f'"{v}"',
                                "disabled": False,
                            }
                        ],
                    }
                ]
            }
            resp = await client.patch(
                endpoint, json=update_payload, headers=headers
            )
            self._check_api_response(resp)
            return True
