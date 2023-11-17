# ---------------------------------------------------------------------
# CSR Proxy: Testing utilities
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import os
from typing import Iterable

# Gufo ACME modules
from gufo.acme.clients.base import ACMEClient

EMAIL = "acme-000000000@gufolabs.com"
DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"


def not_set(vars: Iterable[str]) -> bool:
    """
    Check all environment variables are set.

    Args:
        vars: Iterable of the environment variables names.

    Returns:
        True, if any of the variables is not set
    """
    return any(not os.getenv(v) for v in vars)


def not_set_reason(vars: Iterable[str]) -> str:
    """
    Returns a reason of skip.

    Args:
        vars: Iterable of the environment variables names.

    Returns:
        Skip message.
    """
    vl = ", ".join(vars)
    return f"{vl} variables must be set"


def get_csr_pem(domain: str) -> bytes:
    """Generate CSR for domain in PEM format."""
    private_key = ACMEClient.get_domain_private_key()
    return ACMEClient.get_domain_csr(domain, private_key)
