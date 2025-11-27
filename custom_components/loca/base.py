"""Base classes for Loca entities."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


class LocaEntityMixin:
    """Mixin class providing common functionality for Loca entities."""

    def __init__(self, coordinator, device_id: str) -> None:
        """Initialize the mixin."""
        self.coordinator = coordinator
        self._device_id = device_id

    @property
    def device_data(self) -> dict[str, Any]:
        """Return device data from coordinator with caching."""
        # Cache device data to avoid repeated dictionary lookups
        # Use last_update_success_time for reliable cache invalidation
        # (id() can be reused by Python GC for different objects)
        current_update_time = self.coordinator.last_update_success_time
        if (
            not hasattr(self, '_cached_device_data')
            or getattr(self, '_last_update_time', None) != current_update_time
        ):
            self._cached_device_data = self.coordinator.data.get(self._device_id, {})
            self._last_update_time = current_update_time
        return self._cached_device_data

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.device_data.get("name", f"Loca Device {self._device_id}"),
            manufacturer="Loca",
            model="GPS Tracker",
        )