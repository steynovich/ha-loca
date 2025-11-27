"""Tests for validation utilities."""
from __future__ import annotations

import pytest

from custom_components.loca.const import LocationConstants
from custom_components.loca.validation import (
    DataValidator,
    ValidationError,
)


class TestValidateCoordinates:
    """Test coordinate validation."""

    def test_valid_coordinates(self) -> None:
        """Test validation of valid coordinates."""
        lat, lon = DataValidator.validate_coordinates(52.3676, 4.9041)
        assert lat == 52.3676
        assert lon == 4.9041

    def test_valid_negative_coordinates(self) -> None:
        """Test validation of valid negative coordinates."""
        lat, lon = DataValidator.validate_coordinates(-33.8688, -151.2093)
        assert lat == -33.8688
        assert lon == -151.2093

    def test_string_coordinates(self) -> None:
        """Test validation of string coordinates."""
        lat, lon = DataValidator.validate_coordinates("52.3676", "4.9041")
        assert lat == 52.3676
        assert lon == 4.9041

    def test_boundary_latitude_min(self) -> None:
        """Test validation at minimum latitude boundary."""
        lat, lon = DataValidator.validate_coordinates(-90, 0)
        assert lat == -90
        assert lon == 0

    def test_boundary_latitude_max(self) -> None:
        """Test validation at maximum latitude boundary."""
        lat, lon = DataValidator.validate_coordinates(90, 0)
        assert lat == 90
        assert lon == 0

    def test_boundary_longitude_min(self) -> None:
        """Test validation at minimum longitude boundary."""
        lat, lon = DataValidator.validate_coordinates(0, -180)
        assert lat == 0
        assert lon == -180

    def test_boundary_longitude_max(self) -> None:
        """Test validation at maximum longitude boundary."""
        lat, lon = DataValidator.validate_coordinates(0, 180)
        assert lat == 0
        assert lon == 180

    def test_invalid_latitude_too_high(self) -> None:
        """Test rejection of latitude above 90."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_coordinates(91, 0)
        assert "Latitude" in str(exc_info.value)
        assert "out of valid range" in str(exc_info.value)

    def test_invalid_latitude_too_low(self) -> None:
        """Test rejection of latitude below -90."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_coordinates(-91, 0)
        assert "Latitude" in str(exc_info.value)

    def test_invalid_longitude_too_high(self) -> None:
        """Test rejection of longitude above 180."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_coordinates(0, 181)
        assert "Longitude" in str(exc_info.value)

    def test_invalid_longitude_too_low(self) -> None:
        """Test rejection of longitude below -180."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_coordinates(0, -181)
        assert "Longitude" in str(exc_info.value)

    def test_invalid_coordinate_type(self) -> None:
        """Test rejection of non-numeric coordinate."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_coordinates("invalid", 0)
        assert "Invalid coordinate values" in str(exc_info.value)

    def test_none_coordinates(self) -> None:
        """Test rejection of None coordinates."""
        with pytest.raises(ValidationError):
            DataValidator.validate_coordinates(None, None)


class TestSafeValidateCoordinates:
    """Test safe coordinate validation with fallback."""

    def test_valid_coordinates(self) -> None:
        """Test safe validation of valid coordinates."""
        lat, lon = DataValidator.safe_validate_coordinates(52.3676, 4.9041)
        assert lat == 52.3676
        assert lon == 4.9041

    def test_invalid_coordinates_fallback(self) -> None:
        """Test fallback to (0,0) for invalid coordinates."""
        lat, lon = DataValidator.safe_validate_coordinates(100, 200)
        assert lat == 0.0
        assert lon == 0.0

    def test_none_coordinates_fallback(self) -> None:
        """Test fallback to (0,0) for None coordinates."""
        lat, lon = DataValidator.safe_validate_coordinates(None, None)
        assert lat == 0.0
        assert lon == 0.0

    def test_invalid_type_fallback(self) -> None:
        """Test fallback to (0,0) for invalid type."""
        lat, lon = DataValidator.safe_validate_coordinates("invalid", "invalid")
        assert lat == 0.0
        assert lon == 0.0


class TestValidateBatteryLevel:
    """Test battery level validation."""

    def test_valid_battery_level(self) -> None:
        """Test validation of valid battery level."""
        assert DataValidator.validate_battery_level(50) == 50

    def test_battery_level_zero(self) -> None:
        """Test validation of zero battery level."""
        assert DataValidator.validate_battery_level(0) == 0

    def test_battery_level_hundred(self) -> None:
        """Test validation of 100% battery level."""
        assert DataValidator.validate_battery_level(100) == 100

    def test_battery_level_string(self) -> None:
        """Test validation of string battery level."""
        assert DataValidator.validate_battery_level("75") == 75

    def test_battery_level_float(self) -> None:
        """Test validation of float battery level."""
        assert DataValidator.validate_battery_level(75.5) == 75

    def test_battery_level_above_100_clamped(self) -> None:
        """Test that battery level above 100 is clamped."""
        assert DataValidator.validate_battery_level(150) == 100

    def test_battery_level_below_0_clamped(self) -> None:
        """Test that battery level below 0 is clamped."""
        assert DataValidator.validate_battery_level(-10) == 0

    def test_battery_level_none(self) -> None:
        """Test that None battery level returns None."""
        assert DataValidator.validate_battery_level(None) is None

    def test_battery_level_invalid_string(self) -> None:
        """Test that invalid string returns None."""
        assert DataValidator.validate_battery_level("invalid") is None


class TestValidateGpsAccuracy:
    """Test GPS accuracy validation."""

    def test_valid_accuracy(self) -> None:
        """Test validation of valid GPS accuracy."""
        assert DataValidator.validate_gps_accuracy(10) == 10

    def test_accuracy_string(self) -> None:
        """Test validation of string GPS accuracy."""
        assert DataValidator.validate_gps_accuracy("15") == 15

    def test_accuracy_float(self) -> None:
        """Test validation of float GPS accuracy."""
        assert DataValidator.validate_gps_accuracy(7.5) == 7

    def test_accuracy_none_returns_default(self) -> None:
        """Test that None accuracy returns default."""
        result = DataValidator.validate_gps_accuracy(None)
        assert result == LocationConstants.DEFAULT_GPS_ACCURACY

    def test_accuracy_zero_returns_minimum(self) -> None:
        """Test that zero accuracy is clamped to minimum 1."""
        assert DataValidator.validate_gps_accuracy(0) == 1

    def test_accuracy_negative_returns_minimum(self) -> None:
        """Test that negative accuracy is clamped to minimum 1."""
        assert DataValidator.validate_gps_accuracy(-5) == 1

    def test_accuracy_invalid_returns_default(self) -> None:
        """Test that invalid accuracy returns default."""
        result = DataValidator.validate_gps_accuracy("invalid")
        assert result == LocationConstants.DEFAULT_GPS_ACCURACY


class TestValidateDeviceId:
    """Test device ID validation."""

    def test_valid_device_id(self) -> None:
        """Test validation of valid device ID."""
        assert DataValidator.validate_device_id("12345") == "12345"

    def test_device_id_integer(self) -> None:
        """Test validation of integer device ID."""
        assert DataValidator.validate_device_id(12345) == "12345"

    def test_device_id_with_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        assert DataValidator.validate_device_id("  12345  ") == "12345"

    def test_device_id_empty(self) -> None:
        """Test rejection of empty device ID."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_device_id("")
        assert "cannot be empty" in str(exc_info.value)

    def test_device_id_none(self) -> None:
        """Test rejection of None device ID."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_device_id(None)
        assert "cannot be empty" in str(exc_info.value)

    def test_device_id_whitespace_only(self) -> None:
        """Test rejection of whitespace-only device ID."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_device_id("   ")
        assert "cannot be blank" in str(exc_info.value)


class TestValidateStatusEntry:
    """Test status entry validation."""

    def test_valid_status_entry(self) -> None:
        """Test validation of valid status entry."""
        entry = {
            "Asset": {"id": "12345", "label": "Test"},
            "History": {"latitude": 52.0, "longitude": 4.0},
            "Spot": {"city": "Amsterdam"},
        }
        result = DataValidator.validate_status_entry(entry)
        assert result["Asset"]["id"] == "12345"
        assert result["History"]["latitude"] == 52.0
        assert result["Spot"]["city"] == "Amsterdam"

    def test_status_entry_missing_history(self) -> None:
        """Test validation with missing History."""
        entry = {
            "Asset": {"id": "12345"},
        }
        result = DataValidator.validate_status_entry(entry)
        assert result["Asset"]["id"] == "12345"
        assert result["History"] == {}
        assert result["Spot"] == {}

    def test_status_entry_not_dict(self) -> None:
        """Test rejection of non-dict status entry."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_status_entry("not a dict")
        assert "must be a dictionary" in str(exc_info.value)

    def test_status_entry_missing_asset(self) -> None:
        """Test rejection of status entry without Asset."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_status_entry({"History": {}})
        assert "missing valid Asset data" in str(exc_info.value)

    def test_status_entry_asset_not_dict(self) -> None:
        """Test rejection of status entry with non-dict Asset."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_status_entry({"Asset": "not a dict"})
        assert "missing valid Asset data" in str(exc_info.value)


class TestValidateLocationEntry:
    """Test location entry validation."""

    def test_valid_location_entry(self) -> None:
        """Test validation of valid location entry."""
        entry = {
            "id": "1",
            "label": "Home",
            "latitude": "52.0",
            "longitude": "4.0",
            "radius": "100",
            "city": "Amsterdam",
        }
        result = DataValidator.validate_location_entry(entry)
        assert result["id"] == "1"
        assert result["label"] == "Home"
        assert result["latitude"] == 52.0
        assert result["longitude"] == 4.0
        assert result["radius"] == 100
        assert result["city"] == "Amsterdam"

    def test_location_entry_minimal(self) -> None:
        """Test validation of minimal location entry."""
        entry = {"id": "1"}
        result = DataValidator.validate_location_entry(entry)
        assert result["id"] == "1"
        assert result["label"] == "Location 1"
        assert result["latitude"] == 0.0
        assert result["longitude"] == 0.0

    def test_location_entry_invalid_coordinates(self) -> None:
        """Test handling of invalid coordinates in location entry."""
        entry = {
            "id": "1",
            "latitude": "invalid",
            "longitude": "invalid",
        }
        result = DataValidator.validate_location_entry(entry)
        # Should fallback to (0,0) for invalid coordinates
        assert result["latitude"] == 0.0
        assert result["longitude"] == 0.0

    def test_location_entry_not_dict(self) -> None:
        """Test rejection of non-dict location entry."""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_location_entry("not a dict")
        assert "must be a dictionary" in str(exc_info.value)

    def test_location_entry_negative_radius(self) -> None:
        """Test that negative radius is clamped to minimum 1."""
        entry = {"id": "1", "radius": "-50"}
        result = DataValidator.validate_location_entry(entry)
        assert result["radius"] >= 1
