# ---------------------------------------------------------------------
# Gufo ACME: DavAcmeClient implementation
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""A DavAcmeClient implementation."""

# Python modules
from typing import Any

# Third-party modules
import httpx

from ..error import AcmeFulfillmentFailed

# Gufo ACME modules
from ..types import AcmeChallenge
from .base import AcmeClient

HTTP_MAX_VALID = 299


class DavAcmeClient(AcmeClient):
    """
    WebDAV-compatible ACME Client.

    Fulfills http-01 challenge by uploading
    a token using HTTP PUT/DELETE methods
    with basic authorization.
    Works either with WebDAV modules
    or with custom scripts.

    Args:
        username: DAV user name.
        password: DAV password.
    """

    def __init__(
        self: "DavAcmeClient",
        directory_url: str,
        *,
        username: str,
        password: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(directory_url, **kwargs)
        self.username = username
        self.password = password

    def get_auth(self: "DavAcmeClient") -> httpx.Auth:
        """
        Get Auth for request.

        Returns:
            Auth information to be sent along with
            the request.
        """
        return httpx.BasicAuth(
            username=self.username,
            password=self.password,
        )

    @staticmethod
    def _check_dav_response(resp: httpx.Response) -> None:
        """
        Check DAV response.

        Raise an error if necessary.
        """
        if resp.status_code > HTTP_MAX_VALID:
            msg = f"Failed to put challenge: code {resp.status_code}"
            raise AcmeFulfillmentFailed(msg)

    async def fulfill_http_01(
        self: "DavAcmeClient", domain: str, challenge: AcmeChallenge
    ) -> bool:
        """
        Perform http-01 fullfilment.

        Execute PUT method to place a token.

        Args:
            domain: Domain name
            challenge: AcmeChallenge instance, containing token.

        Returns:
            True - on succeess

        Raises:
            AcmeFulfillmentFailed: On error.
        """
        async with self._get_client() as client:
            v = self.get_key_authorization(challenge)
            resp = await client.put(
                f"http://{domain}/.well-known/acme-challenge/{challenge.token}",
                content=v,
                auth=self.get_auth(),
            )
            self._check_dav_response(resp)
        return True

    async def clear_http_01(
        self: "DavAcmeClient", domain: str, challenge: AcmeChallenge
    ) -> None:
        """
        Remove provisioned token.

        Args:
            domain: Domain name
            challenge: AcmeChallenge instance, containing token.

        Raises:
            AcmeFulfillmentFailed: On error.
        """
        async with self._get_client() as client:
            resp = await client.delete(
                f"http://{domain}/.well-known/acme-challenge/{challenge.token}",
                auth=self.get_auth(),
            )
            self._check_dav_response(resp)
