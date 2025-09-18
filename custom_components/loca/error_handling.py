"""Error handling utilities for Loca integration."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Union

_LOGGER = logging.getLogger(__name__)

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