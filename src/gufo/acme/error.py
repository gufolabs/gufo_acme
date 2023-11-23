# ---------------------------------------------------------------------
# Gufo ACME: Error definitions
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

"""AcmeClient error classes."""


class AcmeError(Exception):
    """Base class for all Gufo Acme errors."""


class AcmeBadNonceError(AcmeError):
    """Server rejects a nounce as invalid."""


class AcmeTimeoutError(AcmeError):
    """Operation timed out."""


class AcmeConnectError(AcmeError):
    """Failed to connect ACME server."""


class AcmeRateLimitError(AcmeError):
    """Request rate limit exceeded."""


class AcmeAlreadyRegistered(AcmeError):
    """Client is alredy registered."""


class AcmeUndecodableError(AcmeError):
    """Cannot decode an error message."""


class AcmeAuthorizationError(AcmeError):
    """Failed to pass an authorization."""


class AcmeFulfillmentFailed(AcmeError):
    """Failed to fulfill challenge."""


class AcmeNotRegistredError(AcmeError):
    """Client is not registred."""


class AcmeUnauthorizedError(AcmeError):
    """Request is not authorized."""


class AcmeCertificateError(AcmeError):
    """Failed to finalize."""


class AcmeExternalAccountRequred(AcmeError):
    """External account binding is required."""
