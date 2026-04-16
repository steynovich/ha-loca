"""The Loca Device Tracker integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .coordinator import LocaDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loca from a config entry."""
    coordinator = LocaDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in runtime_data (modern approach)
    entry.runtime_data = coordinator

    # Reload the entry whenever options change (e.g. scan_interval)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up services if not already registered (thread-safe check)
    if not hass.services.has_service(DOMAIN, "refresh_devices"):
        await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = entry.runtime_data
        if coordinator:
            await coordinator.async_shutdown()

        # Unload services if this is the last config entry being unloaded.
        # The entry being unloaded is still reported as "loaded" at this point,
        # so <= 1 means we are the only remaining loaded entry.
        remaining_entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.state.value == "loaded"
        ]
        if len(remaining_entries) <= 1:
            await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow removal of a device if it is no longer present in the coordinator data."""
    coordinator: LocaDataUpdateCoordinator = entry.runtime_data
    return not device_entry.identifiers.intersection(
        (DOMAIN, device_id) for device_id in coordinator.data
    )
