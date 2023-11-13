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
class ACMEAuthorization(object):
    """
    ACME Authorization resource.

    Attributes:
        domain: Domain name.
        url: Authorization URL.
    """

    domain: str
    url: str


@dataclass
class ACMEOrder(object):
    """
    ACME order resource.

    Attributes:
        authorizations: List of possibile authirizations.
        finalize: URL to finalize the order.
    """

    authorizations: List[ACMEAuthorization]
    finalize: str


@dataclass
class ACMEChallenge(object):
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
class ACMEDirectory(object):
    """
    ACME directory.

    ACME directory is the structure containing
    endpoint urls for given server.

    Attributes:
        new_account: URL to create new account.
        new_nonce: URL to get a new nonce.
        new_order: URL to create a new order.
    """

    new_account: str
    new_nonce: Optional[str]
    new_order: str
