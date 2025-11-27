"""Tests for error handling utilities."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientConnectorError, ServerTimeoutError

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

    def test_log_generic_connectivity_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging of generic connectivity error."""
        logger = logging.getLogger("test")
        err = ConnectionError("Connection reset by peer")

        with caplog.at_level(logging.WARNING):
            log_connectivity_error(logger, "Get groups", err)

        assert "Get groups failed" in caplog.text
        assert "connectivity issue" in caplog.text
        assert "ConnectionError" in caplog.text
        assert "Will retry on next update cycle" in caplog.text

    def test_log_truncates_long_messages(self, caplog: pytest.LogCaptureFixture) -> None:
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
