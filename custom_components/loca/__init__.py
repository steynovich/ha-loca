"""The Loca Device Tracker integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up services on first integration setup (thread-safe check)
    # Only set up services if this is the first config entry
    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        await async_setup_services(hass)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = entry.runtime_data
        if coordinator:
            await coordinator.async_shutdown()
        
        # Unload services if this is the last config entry
        if len(hass.config_entries.async_entries(DOMAIN)) == 1:
            await async_unload_services(hass)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)