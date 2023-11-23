# ---------------------------------------------------------------------
# Gufo ACME: Types definitions
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

"""RFC-8555 compatible ACME protocol structures."""

# Python modules
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AcmeAuthorization(object):
    """
    ACME Authorization resource.

    Attributes:
        domain: Domain name.
        url: Authorization URL.
    """

    domain: str
    url: str


@dataclass
class AcmeOrder(object):
    """
    ACME order resource.

    Attributes:
        authorizations: List of possibile authirizations.
        finalize: URL to finalize the order.
    """

    authorizations: List[AcmeAuthorization]
    finalize: str


@dataclass
class AcmeChallenge(object):
    """
    ACME challenge resource.

    Attributes:
        type: Challenge type, i.e. `http-01`, `dns-01`, ...
        url: Challenge confirmation URL.
        token: Challenge token.
    """

    type: str
    url: str
    token: str


@dataclass
class AcmeDirectory(object):
    """
    ACME directory.

    ACME directory is the structure containing
    endpoint urls for given server.

    Attributes:
        new_account: URL to create new account.
        new_nonce: URL to get a new nonce.
        new_order: URL to create a new order.
        external_account_required: True, if new_account
            requires external account binding.
    """

    new_account: str
    new_nonce: Optional[str]
    new_order: str
    external_account_required: bool


@dataclass
class ExternalAccountBinding(object):
    """
    External account binding for .new_account() method.

    Attributes:
        kid: Key identifier.
        hmac_key: Decoded HMAC key.
    """

    kid: str
    hmac_key: bytes
