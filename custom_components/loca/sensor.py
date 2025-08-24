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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOCA_ASSET_TYPE_ICONS
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


class LocaSensor(CoordinatorEntity, SensorEntity):
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
        super().__init__(coordinator)
        self._device_id = device_id
        self._sensor_type = sensor_type
        self.entity_description = SENSOR_TYPES[sensor_type]
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{sensor_type}"
        # Entity name is handled by entity_description

    @property
    def device_data(self) -> dict[str, Any]:
        """Return device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})

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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}
        
        if self._sensor_type == "last_seen":
            if location_source := self.device_data.get("location_source"):
                attributes["location_source"] = location_source
        elif self._sensor_type == "asset_info":
            # Add all asset information as attributes
            asset_info = self.device_data.get("asset_info", {})
            if asset_info:
                attributes.update({
                    "brand": asset_info.get("brand", "Unknown"),
                    "model": asset_info.get("model", "Unknown"), 
                    "serial": asset_info.get("serial", "Unknown"),
                    "type": asset_info.get("type", "Unknown"),
                    "group_name": asset_info.get("group_name", "Unknown"),
                })
            
            # Add additional device information as attributes
            if signal_strength := self.device_data.get("signal_strength"):
                attributes["gsm_signal_strength"] = signal_strength
            if location_label := self.device_data.get("location_label"):
                attributes["location_label"] = location_label
            if address := self.device_data.get("address"):
                attributes["address"] = address
        elif self._sensor_type == "speed":
            # Add speed-related attributes
            if location_source := self.device_data.get("location_source"):
                attributes["location_source"] = location_source
            if satellites := self.device_data.get("satellites"):
                attributes["satellites"] = satellites
            if gps_accuracy := self.device_data.get("gps_accuracy"):
                attributes["gps_accuracy"] = f"{gps_accuracy}m"
        elif self._sensor_type == "location_update":
            # Add detailed location update configuration as attributes
            location_update = self.device_data.get("location_update", {})
            if location_update:
                # Convert timeofday to HH:MM format
                # Format: timeofday like 91000 means 9:10 (HHMM * 100 + SS format)
                timeofday = location_update.get("timeofday", 0)
                if timeofday and isinstance(timeofday, (int, float)):
                    try:
                        timeofday = int(timeofday)
                        # Parse format: HHMM00 or similar (e.g., 91000 = 9:10)
                        if timeofday >= 1000:
                            # Extract hours and minutes from HHMM00 format
                            hours = timeofday // 10000 if timeofday >= 10000 else 0
                            minutes = (timeofday % 10000) // 100 if timeofday >= 100 else 0
                            # Ensure valid time range
                            hours = min(23, max(0, hours))
                            minutes = min(59, max(0, minutes))
                            attributes["update_time"] = f"{hours:02d}:{minutes:02d}"
                        else:
                            # Fallback: treat as seconds since midnight
                            timeofday = abs(timeofday) % 86400
                            hours = timeofday // 3600 if timeofday >= 3600 else 0
                            minutes = (timeofday % 3600) // 60 if timeofday >= 60 else 0
                            hours = min(23, max(0, hours))
                            minutes = min(59, max(0, minutes))
                            attributes["update_time"] = f"{hours:02d}:{minutes:02d}"
                    except (ValueError, TypeError):
                        # If parsing fails, don't add the update_time attribute
                        pass
                
                attributes.update({
                    "frequency": location_update.get("frequency", 0),
                    "always_on": location_update.get("always", 0) == 1,
                    "begin_time": location_update.get("begin", 0),
                    "end_time": location_update.get("end", 0),
                })
                
                # Convert frequency to human readable format
                frequency = location_update.get("frequency", 0)
                if frequency >= 86400:
                    attributes["frequency_description"] = f"{frequency // 86400} day(s)"
                elif frequency >= 3600:
                    attributes["frequency_description"] = f"{frequency // 3600} hour(s)"
                elif frequency >= 60:
                    attributes["frequency_description"] = f"{frequency // 60} minute(s)"
                else:
                    attributes["frequency_description"] = f"{frequency} second(s)"
        elif self._sensor_type == "location":
            # Add detailed address components as attributes (textual data only)
            address_details = self.device_data.get("address_details", {})
            if address_details:
                # Only add non-empty address components
                for key, value in address_details.items():
                    if value:
                        attributes[key] = value
                
                # Add textual location context information
                if location_label := self.device_data.get("location_label"):
                    attributes["location_label"] = location_label
                
                # Add formatted full address for reference
                if full_address := self.device_data.get("address"):
                    attributes["full_address"] = full_address
                
                # Add GPS satellite information
                if satellites := self.device_data.get("satellites"):
                    attributes["satellites"] = satellites
        
        return attributes

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
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.device_data.get("name", f"Loca Device {self._device_id}"),
            manufacturer="Loca",
            model="GPS Tracker",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self._device_id in self.coordinator.data
            and self.native_value is not None
        )