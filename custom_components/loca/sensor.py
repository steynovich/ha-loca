"""Support for Loca device sensors."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import LocaEntityMixin
from .const import DOMAIN, LOCA_ASSET_TYPE_ICONS, TimeConstants
from .coordinator import LocaDataUpdateCoordinator

SENSOR_TYPES = {
    "battery": SensorEntityDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "last_seen": SensorEntityDescription(
        key="last_seen", 
        name="Last Seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "location_accuracy": SensorEntityDescription(
        key="location_accuracy",
        name="Location Accuracy", 
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,  # Disable by default (noisy)
    ),
    "asset_info": SensorEntityDescription(
        key="asset_info",
        name="Asset Information",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "speed": SensorEntityDescription(
        key="speed",
        name="Speed",
        native_unit_of_measurement="km/h",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    "location_update": SensorEntityDescription(
        key="location_update",
        name="Location Update Config",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "location": SensorEntityDescription(
        key="location",
        name="Location",
        icon="mdi:home-map-marker",
        # entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Loca sensors from a config entry."""
    coordinator: LocaDataUpdateCoordinator = config_entry.runtime_data
    
    entities = []
    for device_id in coordinator.data:
        for sensor_type in SENSOR_TYPES:
            entities.append(LocaSensor(coordinator, device_id, sensor_type))
    
    async_add_entities(entities)
    
    # Note: New devices added after setup will appear after integration reload.
    # This is a Home Assistant limitation for sensor entities.


class LocaSensor(LocaEntityMixin, CoordinatorEntity, SensorEntity):
    """Representation of a Loca sensor."""

    _attr_has_entity_name = True
    parallel_updates = asyncio.Semaphore(1)

    def __init__(
        self,
        coordinator: LocaDataUpdateCoordinator,
        device_id: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        LocaEntityMixin.__init__(self, coordinator, device_id)
        CoordinatorEntity.__init__(self, coordinator)
        self._sensor_type = sensor_type
        self.entity_description = SENSOR_TYPES[sensor_type]
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{sensor_type}"
        # Entity name is handled by entity_description


    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        name = self.entity_description.name
        if name is None or name == "":
            return None
        return str(name)

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._sensor_type == "battery":
            return self.device_data.get("battery_level")
        elif self._sensor_type == "last_seen":
            # For timestamp device class, return the datetime object directly
            return self.device_data.get("last_seen")
        elif self._sensor_type == "location_accuracy":
            return self.device_data.get("gps_accuracy")
        elif self._sensor_type == "asset_info":
            # Return a summary string for the asset
            asset_info = self.device_data.get("asset_info", {})
            brand = asset_info.get("brand", "")
            model = asset_info.get("model", "")
            if brand and model:
                return f"{brand} {model}"
            elif brand:
                return brand
            elif model:
                return model
            else:
                return "Unknown Asset"
        elif self._sensor_type == "speed":
            return self.device_data.get("speed")
        elif self._sensor_type == "location_update":
            # Return a simple summary of the location update configuration
            location_update = self.device_data.get("location_update", {})
            if not location_update:
                return "Not configured"
            
            always = location_update.get("always", 0)
            
            if always == 1:
                return "Always on"
            else:
                return "Scheduled"
        elif self._sensor_type == "location":
            # Return the formatted address as stored in device data
            # Use translation for unknown location when address is None or empty
            address = self.device_data.get("address")
            if address:
                return address
            else:
                # Return fallback text for unknown location
                return "Unknown location"
        
        return None

    def _get_last_seen_attributes(self) -> dict[str, Any]:
        """Get attributes for last_seen sensor."""
        attributes = {}
        if location_source := self.device_data.get("location_source"):
            attributes["location_source"] = location_source
        return attributes

    def _get_asset_info_attributes(self) -> dict[str, Any]:
        """Get attributes for asset_info sensor."""
        attributes = {}
        asset_info = self.device_data.get("asset_info", {})
        if asset_info:
            attributes.update({
                "brand": asset_info.get("brand", "Unknown"),
                "model": asset_info.get("model", "Unknown"),
                "serial": asset_info.get("serial", "Unknown"),
                "type": asset_info.get("type", "Unknown"),
                "group_name": asset_info.get("group_name", "Unknown"),
            })

        # Add additional device information
        for key, attr_name in [
            ("signal_strength", "gsm_signal_strength"),
            ("location_label", "location_label"),
            ("address", "address"),
        ]:
            if value := self.device_data.get(key):
                attributes[attr_name] = value
        return attributes

    def _get_speed_attributes(self) -> dict[str, Any]:
        """Get attributes for speed sensor."""
        attributes = {}
        if location_source := self.device_data.get("location_source"):
            attributes["location_source"] = location_source
        if satellites := self.device_data.get("satellites"):
            attributes["satellites"] = satellites
        if gps_accuracy := self.device_data.get("gps_accuracy"):
            attributes["gps_accuracy"] = f"{gps_accuracy}m"
        return attributes

    def _format_time_of_day(self, timeofday: int | float) -> str | None:
        """Format timeofday value to HH:MM format."""
        try:
            timeofday = int(timeofday)
            if timeofday >= 1000:
                # Extract hours and minutes from HHMM00 format (e.g., 91000 = 9:10)
                hours = timeofday // 10000 if timeofday >= 10000 else 0
                minutes = (timeofday % 10000) // 100 if timeofday >= 100 else 0
            else:
                # Fallback: treat as seconds since midnight
                timeofday = abs(timeofday) % TimeConstants.SECONDS_PER_DAY
                hours = timeofday // TimeConstants.SECONDS_PER_HOUR if timeofday >= TimeConstants.SECONDS_PER_HOUR else 0
                minutes = (timeofday % TimeConstants.SECONDS_PER_HOUR) // TimeConstants.SECONDS_PER_MINUTE if timeofday >= TimeConstants.SECONDS_PER_MINUTE else 0

            # Ensure valid time range using constants
            hours = min(TimeConstants.HOURS_PER_DAY - 1, max(0, hours))
            minutes = min(TimeConstants.MINUTES_PER_HOUR - 1, max(0, minutes))
            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, TypeError):
            return None

    def _get_location_update_attributes(self) -> dict[str, Any]:
        """Get attributes for location_update sensor."""
        attributes: dict[str, Any] = {}
        location_update = self.device_data.get("location_update", {})
        if not location_update:
            return attributes

        # Add formatted update time
        if timeofday := location_update.get("timeofday"):
            if isinstance(timeofday, (int, float)):
                if formatted_time := self._format_time_of_day(timeofday):
                    attributes["update_time"] = formatted_time

        attributes.update({
            "frequency": location_update.get("frequency", 0),
            "always_on": location_update.get("always", 0) == 1,
            "begin_time": location_update.get("begin", 0),
            "end_time": location_update.get("end", 0),
        })

        # Convert frequency to human readable format using constants
        frequency = location_update.get("frequency", 0)
        if frequency >= TimeConstants.SECONDS_PER_DAY:
            attributes["frequency_description"] = f"{frequency // TimeConstants.SECONDS_PER_DAY} day(s)"
        elif frequency >= TimeConstants.SECONDS_PER_HOUR:
            attributes["frequency_description"] = f"{frequency // TimeConstants.SECONDS_PER_HOUR} hour(s)"
        elif frequency >= TimeConstants.SECONDS_PER_MINUTE:
            attributes["frequency_description"] = f"{frequency // TimeConstants.SECONDS_PER_MINUTE} minute(s)"
        else:
            attributes["frequency_description"] = f"{frequency} second(s)"
        return attributes

    def _get_location_attributes(self) -> dict[str, Any]:
        """Get attributes for location sensor."""
        attributes = {}
        address_details = self.device_data.get("address_details", {})

        # Add non-empty address components
        for key, value in address_details.items():
            if value:
                attributes[key] = value

        # Add contextual information
        for key, attr_name in [
            ("location_label", "location_label"),
            ("address", "full_address"),
            ("satellites", "satellites"),
        ]:
            if value := self.device_data.get(key):
                attributes[attr_name] = value
        return attributes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attribute_handlers = {
            "last_seen": self._get_last_seen_attributes,
            "asset_info": self._get_asset_info_attributes,
            "speed": self._get_speed_attributes,
            "location_update": self._get_location_update_attributes,
            "location": self._get_location_attributes,
        }

        handler = attribute_handlers.get(self._sensor_type)
        return handler() if handler else {}

    @property
    def icon(self) -> str | None:
        """Return the icon for the sensor."""
        # For asset_info sensor, use dynamic icon based on asset type
        if self._sensor_type == "asset_info":
            asset_info = self.device_data.get("asset_info", {})
            asset_type = asset_info.get("type", 0)
            return LOCA_ASSET_TYPE_ICONS.get(asset_type, "mdi:radar")
        
        # For other sensors, use the default icon from entity description
        return self.entity_description.icon


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._device_id in self.coordinator.data