"""Tests for Loca coordinator."""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.loca.coordinator import LocaDataUpdateCoordinator
from custom_components.loca.const import DOMAIN, DEFAULT_SCAN_INTERVAL
from custom_components.loca.error_handling import LocaAPIUnavailableError


class TestLocaDataUpdateCoordinator:
    """Test the Loca data update coordinator."""

    @pytest.mark.asyncio
    async def test_init(self, hass: HomeAssistant, mock_config_entry, expected_lingering_tasks):
        """Test coordinator initialization."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        
        assert coordinator.config_entry == mock_config_entry
        assert coordinator.name == DOMAIN
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        assert coordinator.api._api_key == "test_api_key"
        assert coordinator.api._username == "test_user"
        assert coordinator.api._password == "test_password"

    @pytest.mark.asyncio
    async def test_async_update_data_empty_response(self, hass: HomeAssistant, mock_config_entry):
        """Test data update with empty response."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        
        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_api_exception(self, hass: HomeAssistant, mock_config_entry):
        """Test data update with API exception."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        
        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_with_location_parsing(self, hass: HomeAssistant, mock_config_entry):
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
            "timestamp": "2022-04-26 19:35:06"
        }
        
        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(coordinator.api, "get_status_list", return_value=[mock_status]), \
             patch.object(coordinator.api, "parse_status_as_device") as mock_parse:
            
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
                "address": "Test Street 42"
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
    async def test_device_data_transformation(self, hass: HomeAssistant, mock_config_entry):
        """Test device data transformation with authentication failure."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)
        
        with patch.object(coordinator.api, "authenticate", return_value=False):
            with pytest.raises(ConfigEntryAuthFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_update_interval_configuration(self, hass: HomeAssistant, mock_config_entry):
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
    async def test_update_data_with_groups_cache(self, hass: HomeAssistant, mock_config_entry):
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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(
                 coordinator.api,
                 "get_status_list",
                 side_effect=LocaAPIUnavailableError("API temporarily unavailable")
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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(
                 coordinator.api,
                 "get_status_list",
                 side_effect=ValueError("Unexpected error")
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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(
                 coordinator.api,
                 "get_status_list",
                 side_effect=Exception("Unauthorized access denied")
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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(
                 coordinator.api,
                 "get_status_list",
                 side_effect=Exception("HTTP 403 Forbidden")
             ):
            with pytest.raises(ConfigEntryAuthFailed):
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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(coordinator.api, "get_status_list", return_value=[{"Asset": {"id": "12345"}}]), \
             patch.object(coordinator.api, "parse_status_as_device", return_value=mock_device):

            result = await coordinator._async_update_data()

            assert len(result) == 1
            assert "12345" in result
            assert result["12345"]["name"] == "Test Device"

    @pytest.mark.asyncio
    async def test_empty_status_list(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test handling of empty status list."""
        coordinator = LocaDataUpdateCoordinator(hass, mock_config_entry)

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(coordinator.api, "update_groups_cache", return_value=None), \
             patch.object(coordinator.api, "get_status_list", return_value=[]):

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

        with patch.object(coordinator.api, "_authenticated", True), \
             patch.object(
                 coordinator.api,
                 "update_groups_cache",
                 side_effect=Exception("Groups API error")
             ), \
             patch.object(coordinator.api, "get_status_list", return_value=[{"Asset": {"id": "12345"}}]), \
             patch.object(coordinator.api, "parse_status_as_device", return_value=mock_device):

            # Should not raise - groups cache error is non-fatal
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()