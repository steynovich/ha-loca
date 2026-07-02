"""Error handling utilities for Loca integration."""

from __future__ import annotations

import logging

from aiohttp import ClientConnectorError, ServerTimeoutError

_LOGGER = logging.getLogger(__name__)


class LocaAPIUnavailableError(Exception):
    """Exception raised when the Loca API is temporarily unavailable."""

    def __init__(self, message: str = "Loca API is temporarily unavailable") -> None:
        """Initialize the exception."""
        self.message = message
        super().__init__(self.message)


# Connection error types that indicate temporary API unavailability
CONNECTION_ERROR_TYPES = (
    ClientConnectorError,
    ServerTimeoutError,
    TimeoutError,
    ConnectionError,
    OSError,
)

# Error messages that indicate DNS/network issues
NETWORK_ERROR_PATTERNS = [
    "timeout",
    "dns",
    "name or service not known",
    "cannot connect to host",
    "connection refused",
    "network is unreachable",
    "no route to host",
    "temporary failure in name resolution",
]


def is_connectivity_error(err: Exception) -> bool:
    """Check if an exception is a connectivity/network error."""
    if isinstance(err, CONNECTION_ERROR_TYPES):
        return True
    error_str = str(err).lower()
    return any(pattern in error_str for pattern in NETWORK_ERROR_PATTERNS)


def log_connectivity_error(
    logger: logging.Logger, operation: str, err: Exception
) -> None:
    """Log a connectivity error without the full stack trace."""
    error_type = type(err).__name__
    error_msg = str(err)

    # Extract the most relevant part of the error message
    if "Cannot connect to host" in error_msg:
        logger.warning(
            "%s failed: Cannot connect to Loca API (network/DNS issue). "
            "Will retry on next update cycle.",
            operation,
        )
    elif "timeout" in error_msg.lower():
        logger.warning(
            "%s failed: Connection to Loca API timed out. "
            "Will retry on next update cycle.",
            operation,
        )
    else:
        logger.warning(
            "%s failed due to connectivity issue (%s): %s. "
            "Will retry on next update cycle.",
            operation,
            error_type,
            error_msg[:100],
        )


def sanitize_for_logging(value: str | None, show_length: bool = True) -> str:
    """Sanitize sensitive values for logging."""
    if not value:
        return "None"
    if show_length:
        return f"***{len(value)} chars***"
    return "***"
