"""Tests for error handling utilities."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from aiohttp import ClientConnectorError, ServerTimeoutError
import pytest

from custom_components.loca.error_handling import (
    CONNECTION_ERROR_TYPES,
    NETWORK_ERROR_PATTERNS,
    LocaAPIUnavailableError,
    is_connectivity_error,
    log_connectivity_error,
    sanitize_for_logging,
)


class TestLocaAPIUnavailableError:
    """Test LocaAPIUnavailableError exception."""

    def test_default_message(self) -> None:
        """Test exception with default message."""
        err = LocaAPIUnavailableError()
        assert str(err) == "Loca API is temporarily unavailable"
        assert err.message == "Loca API is temporarily unavailable"

    def test_custom_message(self) -> None:
        """Test exception with custom message."""
        err = LocaAPIUnavailableError("Custom error message")
        assert str(err) == "Custom error message"
        assert err.message == "Custom error message"

    def test_exception_inheritance(self) -> None:
        """Test that LocaAPIUnavailableError inherits from Exception."""
        err = LocaAPIUnavailableError()
        assert isinstance(err, Exception)


class TestIsConnectivityError:
    """Test is_connectivity_error function."""

    def test_client_connector_error(self) -> None:
        """Test detection of ClientConnectorError."""
        # Create a mock connection key for ClientConnectorError
        mock_key = MagicMock()
        err = ClientConnectorError(mock_key, OSError("Connection refused"))
        assert is_connectivity_error(err) is True

    def test_server_timeout_error(self) -> None:
        """Test detection of ServerTimeoutError."""
        err = ServerTimeoutError("Timeout")
        assert is_connectivity_error(err) is True

    def test_timeout_error(self) -> None:
        """Test detection of TimeoutError."""
        err = TimeoutError("Request timed out")
        assert is_connectivity_error(err) is True

    def test_connection_error(self) -> None:
        """Test detection of ConnectionError."""
        err = ConnectionError("Connection failed")
        assert is_connectivity_error(err) is True

    def test_os_error(self) -> None:
        """Test detection of OSError."""
        err = OSError("Network unreachable")
        assert is_connectivity_error(err) is True

    def test_dns_error_in_message(self) -> None:
        """Test detection of DNS error via error message."""
        err = Exception("Timeout while contacting DNS servers")
        assert is_connectivity_error(err) is True

    def test_cannot_connect_in_message(self) -> None:
        """Test detection of connection error via error message."""
        err = Exception("Cannot connect to host api.loca.nl:443")
        assert is_connectivity_error(err) is True

    def test_name_resolution_error_in_message(self) -> None:
        """Test detection of name resolution error via error message."""
        err = Exception("Temporary failure in name resolution")
        assert is_connectivity_error(err) is True

    def test_connection_refused_in_message(self) -> None:
        """Test detection of connection refused via error message."""
        err = Exception("Connection refused by server")
        assert is_connectivity_error(err) is True

    def test_network_unreachable_in_message(self) -> None:
        """Test detection of network unreachable via error message."""
        err = Exception("Network is unreachable")
        assert is_connectivity_error(err) is True

    def test_non_connectivity_error(self) -> None:
        """Test that non-connectivity errors return False."""
        err = ValueError("Invalid value")
        assert is_connectivity_error(err) is False

    def test_authentication_error(self) -> None:
        """Test that authentication errors return False."""
        err = Exception("Authentication failed: Invalid credentials")
        assert is_connectivity_error(err) is False

    def test_json_decode_error(self) -> None:
        """Test that JSON decode errors return False."""
        err = Exception("JSON decode error: Unexpected token")
        assert is_connectivity_error(err) is False


class TestLogConnectivityError:
    """Test log_connectivity_error function."""

    def test_log_cannot_connect_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging of 'cannot connect' error."""
        logger = logging.getLogger("test")
        err = Exception("Cannot connect to host api.loca.nl:443 ssl:default")

        with caplog.at_level(logging.WARNING):
            log_connectivity_error(logger, "Get assets", err)

        assert "Get assets failed" in caplog.text
        assert "Cannot connect to Loca API" in caplog.text
        assert "network/DNS issue" in caplog.text
        assert "Will retry on next update cycle" in caplog.text

    def test_log_timeout_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging of timeout error."""
        logger = logging.getLogger("test")
        err = Exception("Connection timeout after 30 seconds")

        with caplog.at_level(logging.WARNING):
            log_connectivity_error(logger, "Authentication", err)

        assert "Authentication failed" in caplog.text
        assert "timed out" in caplog.text
        assert "Will retry on next update cycle" in caplog.text

    def test_log_generic_connectivity_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging of generic connectivity error."""
        logger = logging.getLogger("test")
        err = ConnectionError("Connection reset by peer")

        with caplog.at_level(logging.WARNING):
            log_connectivity_error(logger, "Get groups", err)

        assert "Get groups failed" in caplog.text
        assert "connectivity issue" in caplog.text
        assert "ConnectionError" in caplog.text
        assert "Will retry on next update cycle" in caplog.text

    def test_log_truncates_long_messages(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that long error messages are truncated."""
        logger = logging.getLogger("test")
        long_message = "Error: " + "x" * 200
        err = Exception(long_message)

        with caplog.at_level(logging.WARNING):
            log_connectivity_error(logger, "Test operation", err)

        # Message should be truncated to 100 characters
        assert len(caplog.text) < len(long_message) + 200


class TestSanitizeForLogging:
    """Test sanitize_for_logging function."""

    def test_sanitize_none_value(self) -> None:
        """Test sanitizing None value."""
        assert sanitize_for_logging(None) == "None"

    def test_sanitize_empty_string(self) -> None:
        """Test sanitizing empty string."""
        assert sanitize_for_logging("") == "None"

    def test_sanitize_with_length(self) -> None:
        """Test sanitizing with length shown."""
        result = sanitize_for_logging("test_api_key", show_length=True)
        assert result == "***12 chars***"

    def test_sanitize_without_length(self) -> None:
        """Test sanitizing without length shown."""
        result = sanitize_for_logging("test_api_key", show_length=False)
        assert result == "***"

    def test_sanitize_short_value(self) -> None:
        """Test sanitizing short value."""
        result = sanitize_for_logging("ab", show_length=True)
        assert result == "***2 chars***"


class TestHandleApiErrors:
    """Test handle_api_errors decorator."""

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        """Test that successful calls return the expected value."""
        from custom_components.loca.error_handling import handle_api_errors

        @handle_api_errors(default_return=[], log_prefix="Test op")
        async def my_func() -> list[str]:
            return ["result"]

        result = await my_func()
        assert result == ["result"]

    @pytest.mark.asyncio
    async def test_exception_returns_default(self) -> None:
        """Test that exceptions return the default value."""
        from custom_components.loca.error_handling import handle_api_errors

        @handle_api_errors(default_return=[], log_prefix="Test op")
        async def my_func() -> list[str]:
            raise ValueError("boom")

        result = await my_func()
        assert result == []

    @pytest.mark.asyncio
    async def test_exception_returns_none_default(self) -> None:
        """Test that exceptions return None when no default specified."""
        from custom_components.loca.error_handling import handle_api_errors

        @handle_api_errors()
        async def my_func() -> str:
            raise RuntimeError("fail")

        result = await my_func()
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_logs_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that exceptions are logged."""
        from custom_components.loca.error_handling import handle_api_errors

        @handle_api_errors(log_prefix="My operation")
        async def my_func() -> str:
            raise ValueError("test error message")

        with caplog.at_level(logging.ERROR):
            await my_func()

        assert "My operation failed" in caplog.text


class TestHandleConfigFlowErrors:
    """Test handle_config_flow_errors decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_with_input(self) -> None:
        """Test successful call with user input."""
        from custom_components.loca.error_handling import handle_config_flow_errors

        class FakeFlow:
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

            _current_step = "user"
            _schema: dict[str, str] = {}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        flow = FakeFlow()

        @handle_config_flow_errors
        async def step(self, user_input=None):
            return {"type": "create_entry", "data": user_input}

        result = await step(flow, {"key": "value"})
        assert result["type"] == "create_entry"
        assert result["data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_cannot_connect_error(self) -> None:
        """Test handling of CannotConnect error."""
        from custom_components.loca.error_handling import handle_config_flow_errors

        class FakeFlow:
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

            _current_step = "user"
            _schema: dict[str, str] = {}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        flow = FakeFlow()

        @handle_config_flow_errors
        async def step(self, user_input=None):
            raise self.__class__.CannotConnect()

        result = await step(flow, {"key": "value"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

    @pytest.mark.asyncio
    async def test_invalid_auth_error(self) -> None:
        """Test handling of InvalidAuth error."""
        from custom_components.loca.error_handling import handle_config_flow_errors

        class FakeFlow:
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

            _current_step = "user"
            _schema: dict[str, str] = {}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        flow = FakeFlow()

        @handle_config_flow_errors
        async def step(self, user_input=None):
            raise self.__class__.InvalidAuth()

        result = await step(flow, {"key": "value"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

    @pytest.mark.asyncio
    async def test_unknown_error(self) -> None:
        """Test handling of unknown error."""
        from custom_components.loca.error_handling import handle_config_flow_errors

        class FakeFlow:
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

            _current_step = "user"
            _schema: dict[str, str] = {}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        flow = FakeFlow()

        @handle_config_flow_errors
        async def step(self, user_input=None):
            raise RuntimeError("unexpected")

        result = await step(flow, {"key": "value"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "unknown"}

    @pytest.mark.asyncio
    async def test_no_user_input(self) -> None:
        """Test call with no user input passes through."""
        from custom_components.loca.error_handling import handle_config_flow_errors

        class FakeFlow:
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

        flow = FakeFlow()

        @handle_config_flow_errors
        async def step(self, user_input=None):
            return {"type": "form", "step_id": "user"}

        result = await step(flow, None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"


class TestConfigFlowErrorMixin:
    """Test ConfigFlowErrorMixin class."""

    def test_handle_validation_errors_success(self) -> None:
        """Test successful validation."""
        from custom_components.loca.error_handling import ConfigFlowErrorMixin

        class FakeFlow(ConfigFlowErrorMixin):
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

        flow = FakeFlow()
        result = flow.handle_validation_errors(lambda x: x, {"key": "value"})
        assert result == {"key": "value"}

    def test_handle_validation_errors_cannot_connect(self) -> None:
        """Test CannotConnect exception in validation."""
        from custom_components.loca.error_handling import ConfigFlowErrorMixin

        class FakeFlow(ConfigFlowErrorMixin):
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

        flow = FakeFlow()

        def failing_func(x):
            raise FakeFlow.CannotConnect()

        result = flow.handle_validation_errors(failing_func, {})
        assert result == {"base": "cannot_connect"}

    def test_handle_validation_errors_invalid_auth(self) -> None:
        """Test InvalidAuth exception in validation."""
        from custom_components.loca.error_handling import ConfigFlowErrorMixin

        class FakeFlow(ConfigFlowErrorMixin):
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

        flow = FakeFlow()

        def failing_func(x):
            raise FakeFlow.InvalidAuth()

        result = flow.handle_validation_errors(failing_func, {})
        assert result == {"base": "invalid_auth"}

    def test_handle_validation_errors_unknown(self) -> None:
        """Test unknown exception in validation."""
        from custom_components.loca.error_handling import ConfigFlowErrorMixin

        class FakeFlow(ConfigFlowErrorMixin):
            class CannotConnect(Exception):
                pass

            class InvalidAuth(Exception):
                pass

        flow = FakeFlow()

        def failing_func(x):
            raise RuntimeError("unexpected")

        result = flow.handle_validation_errors(failing_func, {})
        assert result == {"base": "unknown"}


class TestConnectionErrorTypes:
    """Test CONNECTION_ERROR_TYPES constant."""

    def test_contains_expected_types(self) -> None:
        """Test that CONNECTION_ERROR_TYPES contains expected exception types."""
        assert ClientConnectorError in CONNECTION_ERROR_TYPES
        assert ServerTimeoutError in CONNECTION_ERROR_TYPES
        assert TimeoutError in CONNECTION_ERROR_TYPES
        assert ConnectionError in CONNECTION_ERROR_TYPES
        assert OSError in CONNECTION_ERROR_TYPES


class TestNetworkErrorPatterns:
    """Test NETWORK_ERROR_PATTERNS constant."""

    def test_contains_expected_patterns(self) -> None:
        """Test that NETWORK_ERROR_PATTERNS contains expected patterns."""
        expected_patterns = [
            "timeout",
            "dns",
            "cannot connect to host",
            "connection refused",
            "network is unreachable",
        ]
        for pattern in expected_patterns:
            assert pattern in NETWORK_ERROR_PATTERNS, f"Missing pattern: {pattern}"
