# ---------------------------------------------------------------------
# Gufo ACME: Error definitions
# ---------------------------------------------------------------------
# Copyright (C) 2023, Gufo Labs
# ---------------------------------------------------------------------

"""ACMEClient error classes."""


class ACMEError(Exception):
    """Base class for all Gufo Acme errors."""


class ACMEBadNonceError(ACMEError):
    """Server rejects a nounce as invalid."""


class ACMETimeoutError(ACMEError):
    """Operation timed out."""


class ACMEConnectError(ACMEError):
    """Failed to connect ACME server."""


class ACMERateLimitError(ACMEError):
    """Request rate limit exceeded."""


class ACMEAlreadyRegistered(ACMEError):
    """Client is alredy registered."""


class ACMEUndecodableError(ACMEError):
    """Cannot decode an error message."""


class ACMEAuthorizationError(ACMEError):
    """Failed to pass an authorization."""


class ACMEFullfillmentFailed(ACMEError):
    """Failed to fulfill challenge."""


class ACMENotRegistredError(ACMEError):
    """Client is not registred."""


class ACMEUnauthorizedError(ACMEError):
    """Request is not authorized."""


class ACMECertificateError(ACMEError):
    """Failed to finalize."""
