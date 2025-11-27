"""Error handling utilities for Loca integration."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Union

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


def log_connectivity_error(logger: logging.Logger, operation: str, err: Exception) -> None:
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

T = TypeVar('T')


def handle_api_errors(default_return: Any = None, log_prefix: str = "API operation"):
    """Decorator for consistent API error handling."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[Union[T, Any]]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return await func(*args, **kwargs)
            except Exception as err:
                _LOGGER.exception(f"{log_prefix} failed: %s", err)
                return default_return
        return wrapper
    return decorator


def handle_config_flow_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for consistent config flow error handling."""
    @wraps(func)
    async def wrapper(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                return await func(self, user_input)
            except self.__class__.CannotConnect:
                errors["base"] = "cannot_connect"
            except self.__class__.InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception in config flow")
                errors["base"] = "unknown"

            # Return form with errors
            return self.async_show_form(
                step_id=getattr(self, '_current_step', 'user'),
                data_schema=getattr(self, '_schema', {}),
                errors=errors
            )
        return await func(self, user_input)
    return wrapper


def sanitize_for_logging(value: str | None, show_length: bool = True) -> str:
    """Sanitize sensitive values for logging."""
    if not value:
        return "None"
    if show_length:
        return f"***{len(value)} chars***"
    return "***"


class ConfigFlowErrorMixin:
    """Mixin to provide standardized config flow error handling."""

    def handle_validation_errors(self, validation_func, user_input):
        """Handle validation with standardized error mapping."""
        try:
            return validation_func(user_input)
        except self.CannotConnect:
            return {"base": "cannot_connect"}
        except self.InvalidAuth:
            return {"base": "invalid_auth"}
        except Exception:
            _LOGGER.exception("Unexpected validation error")
            return {"base": "unknown"}