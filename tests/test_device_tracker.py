"""Tests for Loca device tracker."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.loca.device_tracker import LocaDeviceTracker, async_setup_entry
from custom_components.loca.const import DOMAIN


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_with_devices(self, hass: HomeAssistant, mock_config_entry):
        """Test setup entry with devices."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "device1": {"name": "Device 1"},
            "device2": {"name": "Device 2"},
        }
        
        mock_config_entry.runtime_data = mock_coordinator
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        
        assert len(entities) == 2
        assert all(isinstance(entity, LocaDeviceTracker) for entity in entities)

    @pytest.mark.asyncio
    async def test_setup_entry_no_devices(self, hass: HomeAssistant, mock_config_entry):
        """Test setup entry with no devices."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}
        
        mock_config_entry.runtime_data = mock_coordinator
        
        async_add_entities = AsyncMock()
        
        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        
        assert len(entities) == 0


class TestLocaDeviceTracker:
    """Test the LocaDeviceTracker entity."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.device_id = "test_device"
        self.device_tracker = LocaDeviceTracker(self.mock_coordinator, self.device_id)

    def test_init(self):
        """Test device tracker initialization."""
        assert self.device_tracker._device_id == "test_device"
        assert self.device_tracker._attr_unique_id == f"{DOMAIN}_test_device"
        assert self.device_tracker.coordinator == self.mock_coordinator

    def test_device_data_exists(self):
        """Test device_data property when device exists."""
        test_data = {
            "name": "Test Device",
            "latitude": 52.3676,
            "longitude": 4.9041,
        }
        self.mock_coordinator.data = {"test_device": test_data}
        
        assert self.device_tracker.device_data == test_data

    def test_device_data_missing(self):
        """Test device_data property when device is missing."""
        self.mock_coordinator.data = {}
        
        assert self.device_tracker.device_data == {}

    def test_name_with_device_name(self):
        """Test name property with device name."""
        self.mock_coordinator.data = {
            "test_device": {"name": "My GPS Tracker"}
        }
        
        assert self.device_tracker.name == "My GPS Tracker"

    def test_name_without_device_name(self):
        """Test name property without device name."""
        self.mock_coordinator.data = {"test_device": {}}
        
        assert self.device_tracker.name == "Loca Device test_device"

    def test_latitude(self):
        """Test latitude property."""
        self.mock_coordinator.data = {
            "test_device": {"latitude": 52.3676}
        }
        
        assert self.device_tracker.latitude == 52.3676

    def test_latitude_missing(self):
        """Test latitude property when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        assert self.device_tracker.latitude is None

    def test_longitude(self):
        """Test longitude property."""
        self.mock_coordinator.data = {
            "test_device": {"longitude": 4.9041}
        }
        
        assert self.device_tracker.longitude == 4.9041

    def test_longitude_missing(self):
        """Test longitude property when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        assert self.device_tracker.longitude is None

    def test_location_accuracy(self):
        """Test location_accuracy property."""
        self.mock_coordinator.data = {
            "test_device": {"gps_accuracy": 5}
        }
        
        assert self.device_tracker.location_accuracy == 5

    def test_location_accuracy_missing(self):
        """Test location_accuracy property when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        assert self.device_tracker.location_accuracy == 0  # Returns 0 when accuracy is not available

    def test_battery_level(self):
        """Test battery_level property."""
        self.mock_coordinator.data = {
            "test_device": {"battery_level": 85}
        }
        
        assert self.device_tracker.battery_level == 85

    def test_battery_level_missing(self):
        """Test battery_level property when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        assert self.device_tracker.battery_level is None

    def test_extra_state_attributes_full(self):
        """Test extra_state_attributes with all data."""
        test_datetime = datetime(2022, 1, 1, 12, 0, 0)
        self.mock_coordinator.data = {
            "test_device": {
                "last_seen": test_datetime,
                "location_source": "GPS",
                "gps_accuracy": 5,
            }
        }
        
        attributes = self.device_tracker.extra_state_attributes
        
        assert attributes["last_seen"] == "2022-01-01T12:00:00"
        assert attributes["location_source"] == "GPS"
        assert attributes["gps_accuracy"] == 5

    def test_extra_state_attributes_partial(self):
        """Test extra_state_attributes with partial data."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_source": "Cell Tower",
            }
        }
        
        attributes = self.device_tracker.extra_state_attributes
        
        assert attributes == {"location_source": "Cell Tower"}

    def test_extra_state_attributes_empty(self):
        """Test extra_state_attributes with no data."""
        self.mock_coordinator.data = {"test_device": {}}
        
        attributes = self.device_tracker.extra_state_attributes
        
        assert attributes == {}

    def test_device_info(self):
        """Test device_info property."""
        self.mock_coordinator.data = {
            "test_device": {"name": "My GPS Tracker"}
        }
        
        device_info = self.device_tracker.device_info
        
        assert isinstance(device_info, dict)  # DeviceInfo is TypedDict
        assert device_info["identifiers"] == {(DOMAIN, "test_device")}
        assert device_info["name"] == "My GPS Tracker"
        assert device_info["manufacturer"] == "Loca"
        assert device_info["model"] == "GPS Tracker"

    def test_device_info_no_name(self):
        """Test device_info property without device name."""
        self.mock_coordinator.data = {"test_device": {}}
        
        device_info = self.device_tracker.device_info
        
        assert device_info["name"] == "Loca Device test_device"

    def test_coordinates_zero_values(self):
        """Test coordinates with zero values."""
        self.mock_coordinator.data = {
            "test_device": {
                "latitude": 0.0,
                "longitude": 0.0,
            }
        }
        
        assert self.device_tracker.latitude == 0.0
        assert self.device_tracker.longitude == 0.0

    def test_coordinates_negative_values(self):
        """Test coordinates with negative values."""
        self.mock_coordinator.data = {
            "test_device": {
                "latitude": -34.6037,
                "longitude": -58.3816,
            }
        }
        
        assert self.device_tracker.latitude == -34.6037
        assert self.device_tracker.longitude == -58.3816

    def test_icon_property_dynamic_mapping(self):
        """Test icon property uses dynamic asset type mapping."""
        # Test car (type 1)
        self.mock_coordinator.data = {
            "test_device": {
                "asset_info": {"type": 1, "brand": "BMW", "model": "X3"}
            }
        }
        
        assert self.device_tracker.icon == "mdi:car"
        
        # Test motorbike (type 9)
        self.mock_coordinator.data["test_device"]["asset_info"]["type"] = 9
        assert self.device_tracker.icon == "mdi:motorcycle"
        
        # Test unknown type (fallback to radar)
        self.mock_coordinator.data["test_device"]["asset_info"]["type"] = 999
        assert self.device_tracker.icon == "mdi:radar"

    def test_icon_property_no_asset_info(self):
        """Test icon property fallback when no asset info."""
        self.mock_coordinator.data = {
            "test_device": {"latitude": 52.0, "longitude": 4.0}
        }
        
        # Should fallback to radar when no asset_info
        assert self.device_tracker.icon == "mdi:radar"