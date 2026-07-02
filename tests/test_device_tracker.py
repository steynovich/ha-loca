"""Tests for Loca device tracker."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
import pytest

from custom_components.loca.const import DOMAIN
from custom_components.loca.device_tracker import LocaDeviceTracker, async_setup_entry


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_with_devices(
        self, hass: HomeAssistant, mock_config_entry
    ):
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


class TestFriendlyNames:
    """Full-setup regression tests for entity naming.

    The tracker used to render "My Car My Car" (device name duplicated) and
    sensors were hardcoded English instead of using the translation catalog.
    """

    @pytest.mark.asyncio
    async def test_friendly_names_via_state_machine(self, hass: HomeAssistant):
        """Test tracker takes the device name and sensors get catalog names."""
        from unittest.mock import patch

        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from custom_components.loca.const import CONF_API_KEY

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Loca",
            data={
                CONF_API_KEY: "test_api_key",
                "username": "test_user",
                "password": "test_password",
            },
            unique_id="test_user_deadbeef",
        )
        entry.add_to_hass(hass)

        status_list = [
            {
                "Asset": {"id": "12345", "label": "My Car"},
                "History": {"latitude": 52.3676, "longitude": 4.9041, "charge": 85},
                "Spot": None,
            }
        ]

        with (
            patch(
                "custom_components.loca.api.LocaAPI.authenticate",
                return_value=True,
            ),
            patch(
                "custom_components.loca.api.LocaAPI.update_groups_cache",
                return_value=None,
            ),
            patch(
                "custom_components.loca.api.LocaAPI.get_status_list",
                return_value=status_list,
            ),
            patch("custom_components.loca.api.LocaAPI.close", return_value=None),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

            tracker_state = hass.states.get("device_tracker.my_car")
            assert tracker_state is not None
            # Regression: was "My Car My Car" with the name property override
            assert tracker_state.attributes["friendly_name"] == "My Car"

            battery_state = hass.states.get("sensor.my_car_battery")
            assert battery_state is not None
            assert battery_state.attributes["friendly_name"] == "My Car Battery"
            assert battery_state.state == "85"

            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()


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

    def test_tracker_takes_device_name(self):
        """Test the tracker uses the main-feature naming pattern.

        Regression test: a `name` property override combined with
        has_entity_name produced duplicated friendly names ("My Car My Car").
        """
        assert "name" not in LocaDeviceTracker.__dict__
        assert self.device_tracker._attr_name is None
        assert self.device_tracker._attr_has_entity_name is True

    def test_tracker_has_translation_key(self):
        """Test the tracker declares the translation key used by icons.json."""
        assert self.device_tracker._attr_translation_key == "default"

    def test_available_when_device_in_coordinator_data(self):
        """Test tracker is available while its device is in coordinator data."""
        self.mock_coordinator.data = {"test_device": {"name": "My GPS Tracker"}}
        self.mock_coordinator.last_update_success = True

        assert self.device_tracker.available is True

    def test_unavailable_when_device_disappears(self):
        """Test tracker becomes unavailable when its device leaves the API.

        Regression test: without an `available` override the tracker kept
        reporting the last known coordinates as live forever.
        """
        self.mock_coordinator.data = {"other_device": {}}
        self.mock_coordinator.last_update_success = True

        assert self.device_tracker.available is False

    def test_latitude(self):
        """Test latitude property."""
        self.mock_coordinator.data = {"test_device": {"latitude": 52.3676}}

        assert self.device_tracker.latitude == 52.3676

    def test_latitude_missing(self):
        """Test latitude property when missing."""
        self.mock_coordinator.data = {"test_device": {}}

        assert self.device_tracker.latitude is None

    def test_longitude(self):
        """Test longitude property."""
        self.mock_coordinator.data = {"test_device": {"longitude": 4.9041}}

        assert self.device_tracker.longitude == 4.9041

    def test_longitude_missing(self):
        """Test longitude property when missing."""
        self.mock_coordinator.data = {"test_device": {}}

        assert self.device_tracker.longitude is None

    def test_location_accuracy(self):
        """Test location_accuracy property."""
        self.mock_coordinator.data = {"test_device": {"gps_accuracy": 5}}

        assert self.device_tracker.location_accuracy == 5

    def test_location_accuracy_missing(self):
        """Test location_accuracy property when missing."""
        self.mock_coordinator.data = {"test_device": {}}

        assert (
            self.device_tracker.location_accuracy == 0
        )  # Returns 0 when accuracy is not available

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
        self.mock_coordinator.data = {"test_device": {"name": "My GPS Tracker"}}

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
            "test_device": {"asset_info": {"type": 1, "brand": "BMW", "model": "X3"}}
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


class TestDeviceTrackerAsyncAddNewDevices:
    """Test the _async_add_new_devices listener in device_tracker setup."""

    @pytest.mark.asyncio
    async def test_new_devices_added_on_coordinator_update(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that new device trackers are added when coordinator data changes."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "device1": {"name": "Device 1"},
        }

        mock_config_entry.runtime_data = mock_coordinator

        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # First call creates initial entities
        assert async_add_entities.call_count == 1
        initial_entities = async_add_entities.call_args_list[0][0][0]
        assert len(initial_entities) == 1

        # Get the listener
        listener_call = mock_coordinator.async_add_listener.call_args[0][0]

        # Simulate coordinator update with new device
        mock_coordinator.data = {
            "device1": {"name": "Device 1"},
            "device2": {"name": "Device 2"},
        }
        listener_call()

        # Second call should create entity only for the new device
        assert async_add_entities.call_count == 2
        new_entities = async_add_entities.call_args_list[1][0][0]
        assert len(new_entities) == 1
        assert all(isinstance(e, LocaDeviceTracker) for e in new_entities)

    @pytest.mark.asyncio
    async def test_no_new_devices_no_call(self, hass: HomeAssistant, mock_config_entry):
        """Test that listener does nothing when no new devices found."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = {
            "device1": {"name": "Device 1"},
        }

        mock_config_entry.runtime_data = mock_coordinator
        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        listener_call = mock_coordinator.async_add_listener.call_args[0][0]

        # Call listener without changing data - no new devices
        listener_call()

        # async_add_entities should still only have been called once (initial)
        assert async_add_entities.call_count == 1
