"""Input validation utilities for Loca integration."""
from __future__ import annotations

import logging
from typing import Any

from .const import LocationConstants
from .types import LocationEntry, StatusEntry

_LOGGER = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""


class DataValidator:
    """Validator for API response data."""

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
        """Validate GPS coordinates."""
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (ValueError, TypeError) as err:
            raise ValidationError(f"Invalid coordinate values: {latitude}, {longitude}") from err

        if not (LocationConstants.MIN_LATITUDE <= lat <= LocationConstants.MAX_LATITUDE):
            raise ValidationError(f"Latitude {lat} out of valid range ({LocationConstants.MIN_LATITUDE}, {LocationConstants.MAX_LATITUDE})")

        if not (LocationConstants.MIN_LONGITUDE <= lon <= LocationConstants.MAX_LONGITUDE):
            raise ValidationError(f"Longitude {lon} out of valid range ({LocationConstants.MIN_LONGITUDE}, {LocationConstants.MAX_LONGITUDE})")

        return lat, lon

    @staticmethod
    def validate_device_id(device_id: Any) -> str:
        """Validate device ID."""
        if not device_id:
            raise ValidationError("Device ID cannot be empty")

        device_id_str = str(device_id).strip()
        if not device_id_str:
            raise ValidationError("Device ID cannot be blank")

        return device_id_str

    @staticmethod
    def validate_battery_level(battery_level: Any) -> int | None:
        """Validate battery level."""
        if battery_level is None:
            return None

        try:
            level = int(float(battery_level))
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid battery level value: %s", battery_level)
            return None

        # Clamp to valid range
        return max(0, min(100, level))

    @staticmethod
    def validate_gps_accuracy(accuracy: Any) -> int:
        """Validate GPS accuracy."""
        try:
            acc = int(float(accuracy)) if accuracy is not None else LocationConstants.DEFAULT_GPS_ACCURACY
            return max(1, acc)  # Ensure positive accuracy
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid GPS accuracy value: %s", accuracy)
            return LocationConstants.DEFAULT_GPS_ACCURACY

    @staticmethod
    def validate_status_entry(entry: dict[str, Any]) -> StatusEntry:
        """Validate status entry structure."""
        if not isinstance(entry, dict):
            raise ValidationError("Status entry must be a dictionary")

        # Check for required nested structures
        asset = entry.get("Asset")
        if not isinstance(asset, dict):
            raise ValidationError("Status entry missing valid Asset data")

        history = entry.get("History", {})
        if not isinstance(history, dict):
            _LOGGER.warning("Status entry missing History data")
            history = {}

        spot = entry.get("Spot", {})
        if not isinstance(spot, dict):
            _LOGGER.debug("Status entry missing Spot data")
            spot = {}

        return {
            "Asset": asset,
            "History": history,
            "Spot": spot,
        }

    @staticmethod
    def validate_location_entry(entry: dict[str, Any]) -> LocationEntry:
        """Validate location entry structure."""
        if not isinstance(entry, dict):
            raise ValidationError("Location entry must be a dictionary")

        # Validate required fields
        entry_id = DataValidator.validate_device_id(entry.get("id"))
        label = entry.get("label", f"Location {entry_id}")

        # Validate coordinates if present
        latitude = entry.get("latitude", 0)
        longitude = entry.get("longitude", 0)

        try:
            lat, lon = DataValidator.validate_coordinates(latitude, longitude)
        except ValidationError as err:
            _LOGGER.warning("Invalid coordinates in location entry: %s", err)
            lat, lon = 0.0, 0.0

        return {
            "id": entry_id,
            "label": str(label),
            "latitude": lat,
            "longitude": lon,
            "radius": max(1, int(entry.get("radius", LocationConstants.DEFAULT_GPS_ACCURACY))),
            "street": str(entry.get("street", "")),
            "number": str(entry.get("number", "")),
            "city": str(entry.get("city", "")),
            "zipcode": str(entry.get("zipcode", "")),
            "country": str(entry.get("country", "")),
            "insert": str(entry.get("insert", "")),
            "update": str(entry.get("update", "")),
        }

    @classmethod
    def safe_validate_coordinates(cls, latitude: Any, longitude: Any) -> tuple[float, float]:
        """Safely validate coordinates with fallback to (0,0)."""
        try:
            return cls.validate_coordinates(latitude, longitude)
        except ValidationError as err:
            _LOGGER.warning("Coordinate validation failed, using (0,0): %s", err)
            return 0.0, 0.0