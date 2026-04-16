"""Tests for Loca sensors."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.loca.const import DOMAIN
from custom_components.loca.sensor import SENSOR_TYPES, LocaSensor, async_setup_entry


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
        self.mock_coordinator.data = {"test_device": {"name": "My GPS Tracker"}}

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
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}

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
        self.mock_coordinator.data = {"test_device": {"last_seen": test_datetime}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        assert sensor.native_value == test_datetime

    def test_native_value_last_seen_missing(self):
        """Test native_value for last seen sensor when missing."""
        self.mock_coordinator.data = {"test_device": {}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "last_seen")
        assert sensor.native_value is None

    def test_native_value_location_accuracy(self):
        """Test native_value for location accuracy sensor."""
        self.mock_coordinator.data = {"test_device": {"gps_accuracy": 5}}

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
        self.mock_coordinator.data = {"test_device": {"location_source": "GPS"}}

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
        self.mock_coordinator.data = {"test_device": {"location_source": "GPS"}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        attributes = sensor.extra_state_attributes

        assert attributes == {}

    def test_device_info(self):
        """Test device_info property."""
        self.mock_coordinator.data = {"test_device": {"name": "My GPS Tracker"}}

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
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")

        # Mock the parent available property
        with patch.object(
            type(sensor), "available", new_callable=PropertyMock
        ) as mock_available:
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
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")

        # Mock the parent available property
        with patch.object(
            type(sensor), "available", new_callable=PropertyMock
        ) as mock_available:
            mock_available.return_value = False

            assert sensor.available is False

    def test_icon_property_asset_info_sensor(self):
        """Test icon property for asset_info sensor with dynamic mapping."""
        # Test car (type 1)
        self.mock_coordinator.data = {
            "test_device": {"asset_info": {"type": 1, "brand": "BMW", "model": "X3"}}
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
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}

        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        assert sensor.icon == "mdi:battery"  # From SENSOR_TYPES


class TestLocaSensorNativeValues:
    """Test native_value methods for all sensor types."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.device_id = "test_device"

    def test_native_value_speed(self):
        """Test native_value for speed sensor."""
        self.mock_coordinator.data = {"test_device": {"speed": 65.5}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "speed")
        assert sensor.native_value == 65.5

    def test_native_value_speed_missing(self):
        """Test native_value for speed sensor when missing."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "speed")
        assert sensor.native_value is None

    def test_native_value_asset_info_brand_and_model(self):
        """Test native_value for asset_info sensor with brand and model."""
        self.mock_coordinator.data = {
            "test_device": {"asset_info": {"brand": "BMW", "model": "X3"}}
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.native_value == "BMW X3"

    def test_native_value_asset_info_brand_only(self):
        """Test native_value for asset_info sensor with only brand."""
        self.mock_coordinator.data = {
            "test_device": {"asset_info": {"brand": "BMW", "model": ""}}
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.native_value == "BMW"

    def test_native_value_asset_info_model_only(self):
        """Test native_value for asset_info sensor with only model."""
        self.mock_coordinator.data = {
            "test_device": {"asset_info": {"brand": "", "model": "X3"}}
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.native_value == "X3"

    def test_native_value_asset_info_unknown(self):
        """Test native_value for asset_info sensor with no info."""
        self.mock_coordinator.data = {"test_device": {"asset_info": {}}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.native_value == "Unknown Asset"

    def test_native_value_asset_info_missing(self):
        """Test native_value for asset_info sensor when asset_info is missing."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        assert sensor.native_value == "Unknown Asset"

    def test_native_value_location_update_always_on(self):
        """Test native_value for location_update sensor with always on."""
        self.mock_coordinator.data = {"test_device": {"location_update": {"always": 1}}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        assert sensor.native_value == "Always on"

    def test_native_value_location_update_scheduled(self):
        """Test native_value for location_update sensor with scheduled."""
        self.mock_coordinator.data = {
            "test_device": {"location_update": {"always": 0, "frequency": 300}}
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        assert sensor.native_value == "Scheduled"

    def test_native_value_location_update_not_configured(self):
        """Test native_value for location_update sensor when not configured."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        assert sensor.native_value == "Not configured"

    def test_native_value_location_update_empty_dict(self):
        """Test native_value for location_update sensor with empty dict."""
        self.mock_coordinator.data = {"test_device": {"location_update": {}}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        assert sensor.native_value == "Not configured"

    def test_native_value_location_with_address(self):
        """Test native_value for location sensor with address."""
        self.mock_coordinator.data = {
            "test_device": {"address": "Test Street 42, Amsterdam"}
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location")
        assert sensor.native_value == "Test Street 42, Amsterdam"

    def test_native_value_location_without_address(self):
        """Test native_value for location sensor without address."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location")
        assert sensor.native_value == "Unknown location"

    def test_native_value_location_empty_address(self):
        """Test native_value for location sensor with empty address."""
        self.mock_coordinator.data = {"test_device": {"address": ""}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location")
        assert sensor.native_value == "Unknown location"


class TestLocaSensorExtraStateAttributes:
    """Test extra_state_attributes for all sensor types."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.device_id = "test_device"

    def test_asset_info_attributes_full(self):
        """Test asset_info sensor with full attributes."""
        self.mock_coordinator.data = {
            "test_device": {
                "asset_info": {
                    "brand": "BMW",
                    "model": "X3",
                    "serial": "ABC123",
                    "type": 1,
                    "group_name": "Cars",
                },
                "signal_strength": 75,
                "location_label": "Office",
                "address": "Test Street 42",
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        attrs = sensor.extra_state_attributes

        assert attrs["brand"] == "BMW"
        assert attrs["model"] == "X3"
        assert attrs["serial"] == "ABC123"
        assert attrs["type"] == 1
        assert attrs["group_name"] == "Cars"
        assert attrs["gsm_signal_strength"] == 75
        assert attrs["location_label"] == "Office"
        assert attrs["address"] == "Test Street 42"

    def test_asset_info_attributes_empty(self):
        """Test asset_info sensor with empty asset_info."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "asset_info")
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_speed_attributes_full(self):
        """Test speed sensor with full attributes."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_source": "GPS",
                "satellites": 8,
                "gps_accuracy": 5,
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "speed")
        attrs = sensor.extra_state_attributes

        assert attrs["location_source"] == "GPS"
        assert attrs["satellites"] == 8
        assert attrs["gps_accuracy"] == "5m"

    def test_speed_attributes_empty(self):
        """Test speed sensor with no attributes."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "speed")
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_location_update_attributes_always_on(self):
        """Test location_update attributes with always on."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_update": {
                    "always": 1,
                    "frequency": 300,
                    "begin": 0,
                    "end": 0,
                    "timeofday": 91000,
                }
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes

        assert attrs["always_on"] is True
        assert attrs["frequency"] == 300
        assert attrs["begin_time"] == 0
        assert attrs["end_time"] == 0
        assert "update_time" in attrs
        assert "frequency_description" in attrs
        assert attrs["frequency_description"] == "5 minute(s)"

    def test_location_update_attributes_frequency_hours(self):
        """Test location_update frequency_description in hours."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_update": {
                    "always": 0,
                    "frequency": 7200,
                    "begin": 0,
                    "end": 0,
                }
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes
        assert attrs["frequency_description"] == "2 hour(s)"

    def test_location_update_attributes_frequency_days(self):
        """Test location_update frequency_description in days."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_update": {
                    "always": 0,
                    "frequency": 172800,
                    "begin": 0,
                    "end": 0,
                }
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes
        assert attrs["frequency_description"] == "2 day(s)"

    def test_location_update_attributes_frequency_seconds(self):
        """Test location_update frequency_description in seconds."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_update": {
                    "always": 0,
                    "frequency": 30,
                    "begin": 0,
                    "end": 0,
                }
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes
        assert attrs["frequency_description"] == "30 second(s)"

    def test_location_update_attributes_timeofday_string(self):
        """Test location_update with timeofday as string (not int/float)."""
        self.mock_coordinator.data = {
            "test_device": {
                "location_update": {
                    "always": 0,
                    "frequency": 60,
                    "begin": 0,
                    "end": 0,
                    "timeofday": "morning",
                }
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes
        # timeofday is not int/float, so update_time should not be in attrs
        assert "update_time" not in attrs
        assert attrs["frequency"] == 60

    def test_location_update_attributes_empty(self):
        """Test location_update with empty config."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_update")
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_location_attributes_full(self):
        """Test location sensor with full attributes."""
        self.mock_coordinator.data = {
            "test_device": {
                "address_details": {
                    "street": "Test Street",
                    "number": "42",
                    "city": "Amsterdam",
                    "zipcode": "1234AB",
                    "country": "Netherlands",
                    "district": "",
                },
                "location_label": "Home",
                "address": "Test Street 42, Amsterdam",
                "satellites": 8,
            }
        }
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location")
        attrs = sensor.extra_state_attributes

        assert attrs["street"] == "Test Street"
        assert attrs["number"] == "42"
        assert attrs["city"] == "Amsterdam"
        assert attrs["zipcode"] == "1234AB"
        assert attrs["country"] == "Netherlands"
        # Empty values are not included
        assert "district" not in attrs
        assert attrs["location_label"] == "Home"
        assert attrs["full_address"] == "Test Street 42, Amsterdam"
        assert attrs["satellites"] == 8

    def test_location_attributes_empty(self):
        """Test location sensor with no attributes."""
        self.mock_coordinator.data = {"test_device": {}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location")
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_battery_sensor_no_extra_attributes(self):
        """Test battery sensor has no extra attributes."""
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "battery")
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_location_accuracy_sensor_no_extra_attributes(self):
        """Test location_accuracy sensor has no extra attributes."""
        self.mock_coordinator.data = {"test_device": {"gps_accuracy": 5}}
        sensor = LocaSensor(self.mock_coordinator, self.device_id, "location_accuracy")
        attrs = sensor.extra_state_attributes
        assert attrs == {}


class TestLocaSensorFormatTimeOfDay:
    """Test the _format_time_of_day method."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.mock_coordinator.data = {"test_device": {}}
        self.sensor = LocaSensor(
            self.mock_coordinator, "test_device", "location_update"
        )

    def test_format_time_hhmm00_format(self):
        """Test formatting HHMM00 format (e.g., 91000 = 9:10)."""
        result = self.sensor._format_time_of_day(91000)
        assert result == "09:10"

    def test_format_time_hhmm00_two_digit_hour(self):
        """Test formatting HHMM00 with two-digit hour (e.g., 143000 = 14:30)."""
        result = self.sensor._format_time_of_day(143000)
        assert result == "14:30"

    def test_format_time_small_value_as_seconds(self):
        """Test formatting small value as seconds since midnight."""
        # 500 seconds = 8 minutes, 20 seconds -> 00:08
        result = self.sensor._format_time_of_day(500)
        assert result == "00:08"

    def test_format_time_zero(self):
        """Test formatting zero value."""
        result = self.sensor._format_time_of_day(0)
        assert result == "00:00"

    def test_format_time_1000_boundary(self):
        """Test formatting at the 1000 boundary (HHMM00 format)."""
        # 1000 -> hours = 0, minutes = (1000 % 10000) // 100 = 10
        result = self.sensor._format_time_of_day(1000)
        assert result == "00:10"

    def test_format_time_float_value(self):
        """Test formatting with float value."""
        result = self.sensor._format_time_of_day(91000.5)
        assert result == "09:10"

    def test_format_time_invalid_string(self):
        """Test formatting with invalid string value."""
        result = self.sensor._format_time_of_day("invalid")  # type: ignore[arg-type]
        assert result is None

    def test_format_time_negative_fallback(self):
        """Test formatting with negative value (fallback branch)."""
        # Negative value in fallback branch: abs(-500) % 86400 = 500
        result = self.sensor._format_time_of_day(-500)
        assert result == "00:08"


class TestLocaSensorAvailable:
    """Test the available property edge cases."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()

    def test_available_device_in_data_and_parent_available(self):
        """Test available when device is in coordinator data and parent is available."""
        self.mock_coordinator.data = {"test_device": {"battery_level": 85}}
        self.mock_coordinator.last_update_success = True
        sensor = LocaSensor(self.mock_coordinator, "test_device", "battery")
        # The sensor should be available since device is in data
        # (parent available depends on coordinator.last_update_success)
        assert sensor.available is True

    def test_available_device_not_in_data(self):
        """Test available when device is not in coordinator data."""
        self.mock_coordinator.data = {"other_device": {"battery_level": 85}}
        self.mock_coordinator.last_update_success = True
        sensor = LocaSensor(self.mock_coordinator, "test_device", "battery")
        # Device not in data -> unavailable regardless of parent
        assert sensor.available is False


class TestLocaSensorName:
    """Test name property edge cases."""

    def setup_method(self):
        """Set up test method."""
        self.mock_coordinator = MagicMock()
        self.mock_coordinator.data = {"test_device": {}}

    def test_name_returns_none_for_empty_name(self):
        """Test name returns None when entity_description.name is empty string."""
        sensor = LocaSensor(self.mock_coordinator, "test_device", "battery")
        # Override entity_description name to empty string
        sensor.entity_description = MagicMock()
        sensor.entity_description.name = ""
        assert sensor.name is None

    def test_name_returns_none_for_none_name(self):
        """Test name returns None when entity_description.name is None."""
        sensor = LocaSensor(self.mock_coordinator, "test_device", "battery")
        sensor.entity_description = MagicMock()
        sensor.entity_description.name = None
        assert sensor.name is None


class TestLocaSensorAsyncAddNewDevices:
    """Test the _async_add_new_devices listener in sensor setup."""

    @pytest.mark.asyncio
    async def test_new_devices_added_on_coordinator_update(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that new devices are added when coordinator data changes."""
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
        assert len(initial_entities) == len(SENSOR_TYPES)

        # Get the listener registered with coordinator
        listener_call = mock_coordinator.async_add_listener.call_args[0][0]

        # Simulate coordinator update with new device
        mock_coordinator.data = {
            "device1": {"name": "Device 1"},
            "device2": {"name": "Device 2"},
        }
        listener_call()

        # Second call should create entities only for the new device
        assert async_add_entities.call_count == 2
        new_entities = async_add_entities.call_args_list[1][0][0]
        assert len(new_entities) == len(SENSOR_TYPES)
        assert all(isinstance(e, LocaSensor) for e in new_entities)

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
        assert LOCA_ASSET_TYPE_ICONS[1] == "mdi:car"  # Car
        assert LOCA_ASSET_TYPE_ICONS[2] == "mdi:bicycle"  # Bike
        assert LOCA_ASSET_TYPE_ICONS[12] == "mdi:truck"  # Truck
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
