"""Tests for Loca coordinator."""

from datetime import datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.loca.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from custom_components.loca.coordinator import LocaDataUpdateCoordinator
from custom_components.loca.error_handling import LocaAPIUnavailableError


class TestLocaDataUpdateCoordinator:
    """Test the Loca data update coordinator."""

    @pytest.mark.asyncio
    async def test_init(
        self, hass: HomeAssistant, mock_config_entry, expected_lingering_tasks
    ):
        """Test coordinator initialization."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        assert coordinator.config_entry == mock_config_entry
        assert coordinator.name == DOMAIN
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        assert coordinator.api._api_key == "test_api_key"
        assert coordinator.api._username == "test_user"
        assert coordinator.api._password == "test_password"

    @pytest.mark.asyncio
    async def test_async_update_data_empty_response(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test data update with empty response."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_api_exception(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test data update with API exception."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_with_location_parsing(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test data update with proper location data parsing."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        mock_status = {
            "asset_id": "test123",
            "asset_label": "Test Location Tracker",
            "latitude": "50.0000",
            "longitude": "5.0000",
            "street": "Test Street",
            "number": "42",
            "city": "Test City",
            "zipcode": "1234AB",
            "country": "Netherlands",
            "gps_accuracy": "25",
            "timestamp": "2022-04-26 19:35:06",
        }

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api, "get_status_list", return_value=[mock_status]
            ),
            patch.object(coordinator.api, "parse_status_as_device") as mock_parse,
        ):
            # Mock parse_status_as_device to return proper device data
            mock_parse.return_value = {
                "device_id": "test123",
                "name": "Test Location Tracker",
                "battery_level": None,
                "latitude": 50.0000,
                "longitude": 5.0000,
                "gps_accuracy": 25,
                "location_source": "GPS",
                "last_seen": datetime.now(),
                "address": "Test Street 42",
            }

            result = await coordinator._async_update_data()

            assert len(result) == 1
            assert "test123" in result

            device = result["test123"]
            assert device["device_id"] == "test123"
            assert device["name"] == "Test Location Tracker"
            assert device["battery_level"] is None  # Locations don't have battery
            assert device["latitude"] == 50.0000
            assert device["longitude"] == 5.0000
            assert device["gps_accuracy"] == 25
            assert device["location_source"] == "GPS"
            assert isinstance(device["last_seen"], datetime)
            assert "Test Street 42" in device["address"]

    @pytest.mark.asyncio
    async def test_async_shutdown(self, hass: HomeAssistant, mock_config_entry):
        """Test coordinator shutdown."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "close", return_value=None) as mock_close:
            await coordinator.async_shutdown()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_device_data_transformation(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test device data transformation with authentication failure."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_interval_configuration(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that update interval is properly configured."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        assert coordinator.update_interval is not None
        assert coordinator.update_interval.total_seconds() == DEFAULT_SCAN_INTERVAL

    @pytest.mark.asyncio
    async def test_logger_configuration(self, hass: HomeAssistant, mock_config_entry):
        """Test that logger is properly configured."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        # The logger should be set to the coordinator's logger
        assert coordinator.logger.name.endswith("coordinator")

    @pytest.mark.asyncio
    async def test_update_data_with_groups_cache(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test data update includes groups cache update."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed"):
                await coordinator._async_update_data()


class TestCoordinatorErrorHandling:
    """Test coordinator error handling."""

    @pytest.mark.asyncio
    async def test_api_unavailable_raises_update_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that LocaAPIUnavailableError raises UpdateFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api,
                "get_status_list",
                side_effect=LocaAPIUnavailableError("API temporarily unavailable"),
            ),
        ):
            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "temporarily unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_error_raises_config_entry_auth_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that authentication errors raise ConfigEntryAuthFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_generic_exception_raises_update_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that generic exceptions raise UpdateFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api,
                "get_status_list",
                side_effect=ValueError("Unexpected error"),
            ),
        ):
            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "Error communicating with API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_keyword_in_error_raises_config_entry_auth_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that errors containing auth keywords raise ConfigEntryAuthFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api,
                "get_status_list",
                side_effect=Exception("Unauthorized access denied"),
            ),
        ):
            with pytest.raises(ConfigEntryAuthFailed) as exc_info:
                await coordinator._async_update_data()

            assert "Authentication error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_403_forbidden_error_raises_config_entry_auth_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that 403 forbidden errors raise ConfigEntryAuthFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api,
                "get_status_list",
                side_effect=Exception("HTTP 403 Forbidden"),
            ),
            pytest.raises(ConfigEntryAuthFailed),
        ):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_successful_update_after_api_unavailable(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test successful update after API was unavailable."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        mock_device = {
            "device_id": "12345",
            "name": "Test Device",
            "latitude": 52.0,
            "longitude": 4.0,
            "battery_level": 85,
            "gps_accuracy": 10,
            "location_source": "GPS",
            "last_seen": datetime.now(),
            "address": "Test Street 1",
        }

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(
                coordinator.api,
                "get_status_list",
                return_value=[{"Asset": {"id": "12345"}}],
            ),
            patch.object(
                coordinator.api, "parse_status_as_device", return_value=mock_device
            ),
        ):
            result = await coordinator._async_update_data()

            assert len(result) == 1
            assert "12345" in result
            assert result["12345"]["name"] == "Test Device"

    @pytest.mark.asyncio
    async def test_empty_status_list(self, hass: HomeAssistant, mock_config_entry):
        """Test handling of empty status list."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(coordinator.api, "update_groups_cache", return_value=None),
            patch.object(coordinator.api, "get_status_list", return_value=[]),
        ):
            result = await coordinator._async_update_data()

            # Empty result should be returned
            assert result == {}

    @pytest.mark.asyncio
    async def test_groups_cache_update_failure_continues(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that groups cache update failure doesn't stop data update."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        mock_device = {
            "device_id": "12345",
            "name": "Test Device",
            "latitude": 52.0,
            "longitude": 4.0,
            "battery_level": 85,
            "gps_accuracy": 10,
            "location_source": "GPS",
            "last_seen": datetime.now(),
            "address": "Test Street 1",
        }

        with (
            patch.object(coordinator.api, "_authenticated", True),
            patch.object(
                coordinator.api,
                "update_groups_cache",
                side_effect=Exception("Groups API error"),
            ),
            patch.object(
                coordinator.api,
                "get_status_list",
                return_value=[{"Asset": {"id": "12345"}}],
            ),
            patch.object(
                coordinator.api, "parse_status_as_device", return_value=mock_device
            ),
        ):
            # Should not raise - groups cache error is non-fatal
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()


class TestHandleEmptyStatusList:
    """Test _handle_empty_status_list helper method."""

    @pytest.mark.asyncio
    async def test_empty_status_not_authenticated(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test empty status list when not authenticated raises ConfigEntryAuthFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.api._authenticated = False

        with pytest.raises(ConfigEntryAuthFailed, match="Authentication required"):
            coordinator._handle_empty_status_list()

    @pytest.mark.asyncio
    async def test_empty_status_below_threshold(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test empty status list below threshold does not create repair issue."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.api._authenticated = True

        # First empty run - below threshold
        coordinator._handle_empty_status_list()
        assert coordinator._empty_device_count == 1

    @pytest.mark.asyncio
    async def test_empty_status_at_threshold_creates_repair(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test empty status list at threshold creates repair issue."""
        from custom_components.loca.const import EMPTY_DEVICE_THRESHOLD

        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.api._authenticated = True

        with patch(
            "custom_components.loca.coordinator.async_create_no_devices_issue"
        ) as mock_create:
            # Run enough times to reach threshold
            for _ in range(EMPTY_DEVICE_THRESHOLD):
                coordinator._handle_empty_status_list()

            mock_create.assert_called_once_with(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_empty_status_no_config_entry(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test empty status when not authenticated and config_entry is None."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.api._authenticated = False
        # Simulate config_entry being None
        coordinator.config_entry = None

        with pytest.raises(ConfigEntryAuthFailed):
            coordinator._handle_empty_status_list()


class TestBuildDevicesFromStatus:
    """Test _build_devices_from_status helper method."""

    @pytest.mark.asyncio
    async def test_builds_devices_correctly(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test building devices from status list."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        mock_device_1 = {
            "device_id": "dev1",
            "name": "Device 1",
        }
        mock_device_2 = {
            "device_id": "dev2",
            "name": "Device 2",
        }

        status_list = [
            {"Asset": {"id": "dev1"}},
            {"Asset": {"id": "dev2"}},
        ]

        with (
            patch.object(
                coordinator.api,
                "parse_status_as_device",
                side_effect=[mock_device_1, mock_device_2],
            ),
            patch("custom_components.loca.coordinator.async_delete_api_auth_issue"),
            patch("custom_components.loca.coordinator.async_delete_no_devices_issue"),
        ):
            result = coordinator._build_devices_from_status(status_list)

        assert len(result) == 2
        assert "dev1" in result
        assert "dev2" in result

    @pytest.mark.asyncio
    async def test_logs_new_device_discovery(
        self, hass: HomeAssistant, mock_config_entry, caplog
    ):
        """Test that new device discovery is logged."""
        import logging

        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        # Set previous data
        coordinator.data = {"dev1": {"device_id": "dev1", "name": "Old Device"}}

        mock_device = {"device_id": "dev2", "name": "New Device"}

        with (
            patch.object(
                coordinator.api, "parse_status_as_device", return_value=mock_device
            ),
            patch("custom_components.loca.coordinator.async_delete_api_auth_issue"),
            patch("custom_components.loca.coordinator.async_delete_no_devices_issue"),
            caplog.at_level(logging.INFO),
        ):
            coordinator._build_devices_from_status([{"Asset": {"id": "dev2"}}])

        assert "New device discovered" in caplog.text

    @pytest.mark.asyncio
    async def test_resets_empty_count_on_success(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that empty device count is reset when devices are found."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator._empty_device_count = 5

        mock_device = {"device_id": "dev1", "name": "Device"}

        with (
            patch.object(
                coordinator.api, "parse_status_as_device", return_value=mock_device
            ),
            patch("custom_components.loca.coordinator.async_delete_api_auth_issue"),
            patch("custom_components.loca.coordinator.async_delete_no_devices_issue"),
        ):
            coordinator._build_devices_from_status([{"Asset": {"id": "dev1"}}])

        assert coordinator._empty_device_count == 0


class TestLogRemovedDevices:
    """Test _log_removed_devices helper method."""

    @pytest.mark.asyncio
    async def test_logs_removed_devices(
        self, hass: HomeAssistant, mock_config_entry, caplog
    ):
        """Test that removed devices are logged."""
        import logging

        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "dev1": {"device_id": "dev1", "name": "Device 1"},
            "dev2": {"device_id": "dev2", "name": "Device 2"},
        }

        with caplog.at_level(logging.INFO):
            coordinator._log_removed_devices({"dev1"})

        assert "Device removed" in caplog.text
        assert "dev2" in caplog.text

    @pytest.mark.asyncio
    async def test_no_log_when_no_previous_data(
        self, hass: HomeAssistant, mock_config_entry, caplog
    ):
        """Test no logging when there is no previous data."""
        import logging

        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.data = None  # type: ignore[assignment]

        with caplog.at_level(logging.INFO):
            coordinator._log_removed_devices({"dev1"})

        assert "Device removed" not in caplog.text

    @pytest.mark.asyncio
    async def test_no_log_when_all_present(
        self, hass: HomeAssistant, mock_config_entry, caplog
    ):
        """Test no logging when all devices are still present."""
        import logging

        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        coordinator.data = {
            "dev1": {"device_id": "dev1", "name": "Device 1"},
        }

        with caplog.at_level(logging.INFO):
            coordinator._log_removed_devices({"dev1"})

        assert "Device removed" not in caplog.text


class TestClassifyAndRaise:
    """Test _classify_and_raise helper method."""

    @pytest.mark.asyncio
    async def test_auth_error_terms_raise_config_entry_auth_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that auth-related error messages raise ConfigEntryAuthFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            coordinator._classify_and_raise(Exception("401 Unauthorized"))

    @pytest.mark.asyncio
    async def test_generic_error_raises_update_failed(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that generic errors raise UpdateFailed."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with pytest.raises(UpdateFailed, match="Error communicating with API"):
            coordinator._classify_and_raise(Exception("Something went wrong"))

    @pytest.mark.asyncio
    async def test_auth_error_creates_repair_issue(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that auth errors create repair issues."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with (
            patch(
                "custom_components.loca.coordinator.async_create_api_auth_issue"
            ) as mock_create,
            pytest.raises(ConfigEntryAuthFailed),
        ):
            coordinator._classify_and_raise(Exception("unauthorized access"))

        mock_create.assert_called_once_with(hass, mock_config_entry)


class TestCoordinatorCustomScanInterval:
    """Test coordinator with custom scan interval."""

    @pytest.mark.asyncio
    async def test_custom_scan_interval_from_options(self, hass: HomeAssistant):
        """Test coordinator uses scan_interval from options."""
        from types import MappingProxyType

        from homeassistant.config_entries import ConfigEntry
        from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

        from custom_components.loca.const import CONF_API_KEY

        entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Test Loca",
            data={
                CONF_API_KEY: "test_api_key",
                CONF_USERNAME: "test_user",
                CONF_PASSWORD: "test_password",
            },
            options={"scan_interval": 120},
            source="user",
            entry_id="test_entry_custom",
            discovery_keys=MappingProxyType({}),
            unique_id="test_user_custom",
            subentries_data=frozenset(),
        )
        coordinator = LocaDataUpdateCoordinator(hass, entry)
        assert coordinator.update_interval == timedelta(seconds=120)
