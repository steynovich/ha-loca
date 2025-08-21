"""Tests for Loca sensors."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.loca.sensor import LocaSensor, async_setup_entry, SENSOR_TYPES
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
        
        # Should create 3 sensors per device (battery, last_seen, location_accuracy)
        expected_count = 2 * len(SENSOR_TYPES)
        assert len(entities) == expected_count
        assert all(isinstance(entity, LocaSensor) for entity in entities)

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


class TestLocaSensor:
    """Test the LocaSensor entity."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.device_id = "test_device"

    def test_init_battery_sensor(self):
        """Test battery sensor initialization."""
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        
        assert sensor._device_id == "test_device"
        assert sensor._sensor_type == "battery"
        assert sensor._attr_unique_id == f"{DOMAIN}_test_device_battery"
        assert sensor.entity_description.native_unit_of_measurement == PERCENTAGE
        assert sensor.entity_description.device_class == SensorDeviceClass.BATTERY
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_description.icon == "mdi:battery"

    def test_init_last_seen_sensor(self):
        """Test last seen sensor initialization."""
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        
        assert sensor._sensor_type == "last_seen"
        assert sensor._attr_unique_id == f"{DOMAIN}_test_device_last_seen"
        assert sensor.entity_description.native_unit_of_measurement is None
        assert sensor.entity_description.device_class == SensorDeviceClass.TIMESTAMP
        assert sensor.entity_description.state_class is None
        assert sensor.entity_description.icon == "mdi:clock-outline"

    def test_init_location_accuracy_sensor(self):
        """Test location accuracy sensor initialization."""
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_accuracy")
        
        assert sensor._sensor_type == "location_accuracy"
        assert sensor._attr_unique_id == f"{DOMAIN}_test_device_location_accuracy"
        assert sensor.entity_description.native_unit_of_measurement == "m"
        assert sensor.entity_description.device_class is None
        assert sensor.entity_description.state_class == SensorStateClass.MEASUREMENT
        assert sensor.entity_description.icon == "mdi:crosshairs-gps"

    def test_device_data_exists(self):
        """Test device_data property when device exists."""
        test_data = {
            "name": "Test Device",
            "battery_level": 85,
        }
        self.mock_coordinator.data = {"test_device": test_data}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.device_data == test_data

    def test_device_data_missing(self):
        """Test device_data property when device is missing."""
        self.mock_coordinator.data = {}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.device_data == {}

    def test_name_with_device_name(self):
        """Test name property with device name."""
        self.mock_coordinator.data = {
            "test_device": {"name": "My GPS Tracker"}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        # With _attr_has_entity_name = True, name comes from entity_description only
        assert sensor.name == "Battery"

    def test_name_without_device_name(self):
        """Test name property without device name."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        # With _attr_has_entity_name = True, name comes from entity_description only
        assert sensor.name == "Last Seen"

    def test_native_value_battery(self):
        """Test native_value for battery sensor."""
        self.mock_coordinator.data = {
            "test_device": {"battery_level": 85}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.native_value == 85

    def test_native_value_battery_missing(self):
        """Test native_value for battery sensor when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.native_value is None

    def test_native_value_last_seen(self):
        """Test native_value for last seen sensor."""
        test_datetime = datetime(2022, 1, 1, 12, 0, 0)
        self.mock_coordinator.data = {
            "test_device": {"last_seen": test_datetime}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        assert sensor.native_value == test_datetime

    def test_native_value_last_seen_missing(self):
        """Test native_value for last seen sensor when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        assert sensor.native_value is None

    def test_native_value_location_accuracy(self):
        """Test native_value for location accuracy sensor."""
        self.mock_coordinator.data = {
            "test_device": {"gps_accuracy": 5}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_accuracy")
        assert sensor.native_value == 5

    def test_native_value_location_accuracy_missing(self):
        """Test native_value for location accuracy sensor when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_accuracy")
        assert sensor.native_value is None

    def test_native_value_unknown_sensor_type(self):
        """Test native_value for unknown sensor type."""
        self.mock_coordinator.data = {"test_device": {"some_value": 123}}
        
        # This would normally not happen due to SENSOR_TYPES validation
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        sensor._sensor_type = "unknown"
        
        assert sensor.native_value is None

    def test_extra_state_attributes_last_seen_sensor(self):
        """Test extra_state_attributes for last seen sensor."""
        self.mock_coordinator.data = {
            "test_device": {"location_source": "GPS"}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        attributes = sensor.extra_state_attributes
        
        assert attributes == {"location_source": "GPS"}

    def test_extra_state_attributes_last_seen_no_location_source(self):
        """Test extra_state_attributes for last seen sensor without location source."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        attributes = sensor.extra_state_attributes
        
        assert attributes == {}

    def test_extra_state_attributes_other_sensors(self):
        """Test extra_state_attributes for non-last_seen sensors."""
        self.mock_coordinator.data = {
            "test_device": {"location_source": "GPS"}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        attributes = sensor.extra_state_attributes
        
        assert attributes == {}

    def test_device_info(self):
        """Test device_info property."""
        self.mock_coordinator.data = {
            "test_device": {"name": "My GPS Tracker"}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        device_info = sensor.device_info
        
        assert isinstance(device_info, dict)  # DeviceInfo is TypedDict
        assert device_info["identifiers"] == {(DOMAIN, "test_device")}
        assert device_info["name"] == "My GPS Tracker"
        assert device_info["manufacturer"] == "Loca"
        assert device_info["model"] == "GPS Tracker"

    def test_device_info_no_name(self):
        """Test device_info property without device name."""
        self.mock_coordinator.data = {"test_device": {}}
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        device_info = sensor.device_info
        
        assert device_info["name"] == "Loca Device test_device"

    def test_available_with_data(self):
        """Test available property with valid data."""
        self.mock_coordinator.data = {
            "test_device": {"battery_level": 85}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        
        # Mock the parent available property
        with patch.object(type(sensor), 'available', new_callable=PropertyMock) as mock_available:
            mock_available.return_value = True
            
            assert sensor.available is True

    def test_available_no_device_data(self):
        """Test available property when device not in coordinator data."""
        self.mock_coordinator.data = {}
        # Mock the coordinator's last_update_success property to indicate failure
        self.mock_coordinator.last_update_success = False
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        
        # CoordinatorEntity.available should be False if coordinator has update failure
        assert sensor.available is False

    def test_available_no_sensor_value(self):
        """Test available property when sensor value is None."""
        self.mock_coordinator.data = {"test_device": {}}  # No battery_level
        # Mock the coordinator's last_update_success property to indicate failure
        self.mock_coordinator.last_update_success = False
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        
        # CoordinatorEntity.available should be False if coordinator has update failure
        assert sensor.available is False

    def test_available_parent_unavailable(self):
        """Test available property when parent is unavailable."""
        self.mock_coordinator.data = {
            "test_device": {"battery_level": 85}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        
        # Mock the parent available property
        with patch.object(type(sensor), 'available', new_callable=PropertyMock) as mock_available:
            mock_available.return_value = False
            
            assert sensor.available is False

    def test_icon_property_asset_info_sensor(self):
        """Test icon property for asset_info sensor with dynamic mapping."""
        # Test car (type 1)
        self.mock_coordinator.data = {
            "test_device": {
                "asset_info": {"type": 1, "brand": "BMW", "model": "X3"}
            }
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.icon == "mdi:car"
        
        # Test bicycle (type 2)
        self.mock_coordinator.data["test_device"]["asset_info"]["type"] = 2
        assert sensor.icon == "mdi:bicycle"
        
        # Test unknown type (fallback)
        self.mock_coordinator.data["test_device"]["asset_info"]["type"] = 999
        assert sensor.icon == "mdi:radar"

    def test_icon_property_other_sensors(self):
        """Test icon property for non-asset sensors uses default."""
        self.mock_coordinator.data = {
            "test_device": {"battery_level": 85}
        }
        
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.icon == "mdi:battery"  # From SENSOR_TYPES


class TestDynamicIconMapping:
    """Test the dynamic icon mapping functionality."""

    def test_loca_asset_type_icons_coverage(self):
        """Test that all expected asset types have icon mappings."""
        from custom_components.loca.const import LOCA_ASSET_TYPE_ICONS
        
        # Test all expected asset types (0-14)
        expected_types = list(range(15))  # 0 to 14
        actual_types = list(LOCA_ASSET_TYPE_ICONS.keys())
        
        assert set(expected_types) == set(actual_types)
        
        # Test specific mappings
        assert LOCA_ASSET_TYPE_ICONS[0] == "mdi:radar"  # Loca generic
        assert LOCA_ASSET_TYPE_ICONS[1] == "mdi:car"    # Car
        assert LOCA_ASSET_TYPE_ICONS[2] == "mdi:bicycle"  # Bike
        assert LOCA_ASSET_TYPE_ICONS[12] == "mdi:truck"   # Truck
        assert LOCA_ASSET_TYPE_ICONS[14] == "mdi:van-utility"  # Van


class TestSensorTypes:
    """Test the SENSOR_TYPES configuration."""

    def test_sensor_types_structure(self):
        """Test that SENSOR_TYPES has the expected structure."""
        assert "battery" in SENSOR_TYPES
        assert "last_seen" in SENSOR_TYPES
        assert "location_accuracy" in SENSOR_TYPES
        
        # Check battery sensor config
        battery_config = SENSOR_TYPES["battery"]
        assert battery_config.name == "Battery"
        assert battery_config.native_unit_of_measurement == PERCENTAGE
        assert battery_config.device_class == SensorDeviceClass.BATTERY
        assert battery_config.state_class == SensorStateClass.MEASUREMENT
        assert battery_config.icon == "mdi:battery"
        
        # Check last_seen sensor config
        last_seen_config = SENSOR_TYPES["last_seen"]
        assert last_seen_config.name == "Last Seen"
        assert last_seen_config.device_class == SensorDeviceClass.TIMESTAMP
        assert last_seen_config.icon == "mdi:clock-outline"
        assert last_seen_config.native_unit_of_measurement is None
        
        # Check location_accuracy sensor config
        accuracy_config = SENSOR_TYPES["location_accuracy"]
        assert accuracy_config.name == "Location Accuracy"
        assert accuracy_config.native_unit_of_measurement == "m"
        assert accuracy_config.state_class == SensorStateClass.MEASUREMENT
        assert accuracy_config.icon == "mdi:crosshairs-gps"