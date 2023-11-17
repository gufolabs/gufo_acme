# ---------------------------------------------------------------------
# Gufo ACME: WebACMEClient implementation
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""A WebACMEClient implementation."""

# Python modules
import os
from pathlib import Path
from typing import Any, Union

# Gufo ACME modules
from ..log import logger
from ..types import ACMEChallenge
from .base import ACMEClient


class WebACMEClient(ACMEClient):
    """
    A webserver-backed ACME client.

    Fulfills http-01 challenge by creating
    and removing token files in predefined
    directories.

    Args:
        path: Path mapped to /.well-known/acme-challenges
            directory.
    """

    def __init__(
        self: "WebACMEClient",
        directory_url: str,
        *,
        path: Union[str, Path],
        **kwargs: Any,
    ) -> None:
        super().__init__(directory_url, **kwargs)
        self.path = Path(path)

    def _get_path(self: "WebACMEClient", challenge: ACMEChallenge) -> Path:
        """
        Get Path for challenge.

        Args:
            challenge: ACME challenge

        Returns:
            token path.
        """
        return self.path / Path(challenge.token)

    async def fulfill_http_01(
        self: "WebACMEClient", domain: str, challenge: ACMEChallenge
    ) -> bool:
        """
        Perform http-01 fullfilment.

        Put token to <path>/<token> file.

        Args:
            domain: Domain name
            challenge: ACMEChallenge instance, containing token.

        Returns:
            True - on succeess

        Raises:
            ACMEFulfillmentFailed: On error.
        """
        path = self._get_path(challenge)
        v = self.get_key_authorization(challenge)
        logger.warning("Writing token to %s", path)
        with open(path, "wb") as fp:
            fp.write(v)
        return True

    async def clear_http_01(
        self: "WebACMEClient", domain: str, challenge: ACMEChallenge
    ) -> None:
        """
        Remove provisioned token.

        Args:
            domain: Domain name
            challenge: ACMEChallenge instance, containing token.

        Raises:
            ACMEFulfillmentFailed: On error.
        """
        path = self._get_path(challenge)
        if os.path.exists(path):
            logger.warning("Removing token from %s", path)
            os.unlink(path)
