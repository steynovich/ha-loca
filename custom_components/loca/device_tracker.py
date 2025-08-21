"""Support for Loca device tracking."""
from __future__ import annotations

import logging
import asyncio
from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOCA_ASSET_TYPE_ICONS
from .coordinator import LocaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Loca device tracker from a config entry."""
    coordinator: LocaDataUpdateCoordinator = config_entry.runtime_data
    
    entities = []
    for device_id in coordinator.data:
        entities.append(LocaDeviceTracker(coordinator, device_id))
    
    async_add_entities(entities)


class LocaDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a Loca device tracker."""

    _attr_has_entity_name = True
    parallel_updates = asyncio.Semaphore(1)

    def __init__(
        self, coordinator: LocaDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        self._attr_name = None  # Use device name

    @property
    def device_data(self) -> dict[str, Any]:
        """Return device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return self.device_data.get("name", f"Loca Device {self._device_id}")

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.device_data.get("latitude")

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.device_data.get("longitude")

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        accuracy = self.device_data.get("gps_accuracy")
        if accuracy is None:
            return 0  # Return 0 if accuracy is not available
        return int(accuracy)

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        return self.device_data.get("battery_level")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attributes = {}
        
        if last_seen := self.device_data.get("last_seen"):
            attributes["last_seen"] = last_seen.isoformat()
        
        if self.device_data.get("location_source"):
            attributes["location_source"] = self.device_data["location_source"]
        
        if self.device_data.get("gps_accuracy"):
            attributes["gps_accuracy"] = self.device_data["gps_accuracy"]
            
        return attributes

    @property
    def icon(self) -> str | None:
        """Return the icon for the device based on asset type."""
        asset_info = self.device_data.get("asset_info", {})
        asset_type = asset_info.get("type", 0)
        return LOCA_ASSET_TYPE_ICONS.get(asset_type, "mdi:radar")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.device_data.get("name", f"Loca Device {self._device_id}"),
            manufacturer="Loca",
            model="GPS Tracker",
        )