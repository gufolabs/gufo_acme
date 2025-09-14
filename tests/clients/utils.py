# ---------------------------------------------------------------------
# CSR Proxy: Testing utilities
# ---------------------------------------------------------------------
# Copyright (C) 2023-25, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable

from josepy.jwk import JWKRSA

# Gufo ACME modules
from gufo.acme.clients.base import AcmeClient

EMAIL = "acme-000000000@gufolabs.com"
LE_STAGE_DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"
GOOGLE_STAGE_DIRECTORY = "https://dv.acme-v02.test-api.pki.goog/directory"

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
    private_key = AcmeClient.get_domain_private_key()
    return AcmeClient.get_domain_csr(domain, private_key)


@dataclass
class ResponseStub(object):
    status: int
    headers: Dict[str, bytes] = field(default_factory=dict)
    content: bytes = b""
