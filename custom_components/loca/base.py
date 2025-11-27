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
        """Return device data from coordinator."""
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.get(self._device_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.device_data.get("name", f"Loca Device {self._device_id}"),
            manufacturer="Loca",
            model="GPS Tracker",
        )