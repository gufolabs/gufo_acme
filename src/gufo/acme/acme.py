# ---------------------------------------------------------------------
# Gufo ACME: ACME Messages
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------
"""ACME protocol JWS structures."""

# Python modules
from typing import Any, Dict, Optional, Type

# Third-party modules
from josepy.json_util import encode_b64jose, field
from josepy.jwa import JWASignature
from josepy.jwk import JWK
from josepy.jws import JWS, Header, Signature


class AcmeHeader(Header):
    """
    Structure for ACME JWS header.

    Attributes:
        nonce: Request nonce.
        kid: Account URL.
        url: Request URL.
    """

    nonce: Optional[bytes] = field(
        "nonce", omitempty=True, encoder=encode_b64jose
    )
    kid: Optional[str] = field("kid", omitempty=True)
    url: Optional[str] = field("url", omitempty=True)


class AcmeSignature(Signature):
    """Signature for ACME JWS."""

    __slots__ = Signature._orig_slots
    header_cls = AcmeHeader
    header: AcmeHeader = field(
        "header",
        omitempty=True,
        default=header_cls(),
        decoder=header_cls.from_json,
    )


class AcmeJWS(JWS):
    """Signed JWS for ACME protocol."""

    signature_cls = AcmeSignature
    __slots__ = JWS._orig_slots

    @classmethod
    def sign(  # type: ignore
        cls: Type["AcmeJWS"],
        payload: bytes,
        *,
        key: JWK,
        alg: JWASignature,
        nonce: Optional[bytes] = None,
        url: Optional[str] = None,
        kid: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> JWS:
        """
        Sign a payload and return signed JWS.

        Args:
            payload: Request payload.
            key: Account key.
            alg: Signature algorithm.
            nonce: Request nonce.
            url: Request URL.
            kid: Account URL, if bound.
            kwargs: Other arguments.

        Returns:
            Signed JWS.
        """
        return super().sign(
            payload,
            key=key,
            alg=alg,
            protect=frozenset(["nonce", "url", "kid", "jwk", "alg"]),
            nonce=nonce,
            url=url,
            kid=kid,
            include_jwk=kid is None,
            **kwargs,
        )
