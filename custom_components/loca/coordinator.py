"""DataUpdateCoordinator for Loca."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LocaAPI
from .repairs import (
    async_create_api_auth_issue,
    async_create_no_devices_issue,
    async_delete_api_auth_issue,
    async_delete_no_devices_issue,
)
from .const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    APIConstants,
)

_LOGGER = logging.getLogger(__name__)


class LocaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Loca API."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = LocaAPI(
            config_entry.data[CONF_API_KEY],
            config_entry.data[CONF_USERNAME], 
            config_entry.data[CONF_PASSWORD],
            hass=hass,
        )
        self._empty_device_count = 0

        # Get scan interval from options or use default
        scan_interval = config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Try to authenticate if not already done
            if not self.api.is_authenticated:
                auth_success = await self.api.authenticate()
                if not auth_success:
                    raise ConfigEntryAuthFailed("Authentication failed")
            
            # Update groups cache for group name lookup
            await self.api.update_groups_cache()
            
            # Get device status data from StatusList (this contains the real GPS tracking data)
            status_list = await self.api.get_status_list()
            
            _LOGGER.debug("Fetched %s status entries from StatusList", len(status_list) if status_list else 0)
            
            # Handle empty status list
            if not status_list:
                if self.api.is_authenticated:
                    _LOGGER.info("No devices found in Loca StatusList - account may be empty or devices not configured")
                    # Only create repair issue if this persists (not on first few attempts)
                    self._empty_device_count += 1
                    if self._empty_device_count >= 3:  # After 3 consecutive empty responses
                        if self.config_entry is not None:
                            async_create_no_devices_issue(self.hass, self.config_entry)
                else:
                    _LOGGER.error("Not authenticated when trying to get status list")
                    if self.config_entry is not None:
                        async_create_api_auth_issue(self.hass, self.config_entry)
                    raise ConfigEntryAuthFailed("Authentication required")
            
            devices = {}
            new_device_ids = set()
            
            # Create devices from StatusList entries (these contain real-time tracking data)
            for status_entry in status_list:
                device_data = self.api.parse_status_as_device(status_entry)
                device_id = device_data["device_id"]
                devices[device_id] = device_data
                new_device_ids.add(device_id)
                
                # Check if this is a new device
                if self.data and device_id not in self.data:
                    _LOGGER.info("New device discovered: %s (%s)", device_data.get("name", "Unknown"), device_id)
            
            # Check for removed devices
            if self.data:
                removed_devices = set(self.data.keys()) - new_device_ids
                for removed_id in removed_devices:
                    device_name = self.data.get(removed_id, {}).get("name", "Unknown")
                    _LOGGER.info("Device removed: %s (%s)", device_name, removed_id)
            
            _LOGGER.debug("Updated data for %s devices", len(devices))
            
            # Clear repair issues and reset counter on successful device discovery
            if devices:
                async_delete_api_auth_issue(self.hass)
                async_delete_no_devices_issue(self.hass)
                # Reset empty device counter
                self._empty_device_count = 0
            
            return devices
            
        except ConfigEntryAuthFailed:
            # Re-raise auth errors to trigger reauth flow
            raise
        except Exception as err:
            # Check if error is authentication related
            error_str = str(err).lower()
            if any(term in error_str for term in APIConstants.AUTH_ERROR_TERMS):
                if self.config_entry is not None:
                    async_create_api_auth_issue(self.hass, self.config_entry)
                raise ConfigEntryAuthFailed(f"Authentication error: {err}") from err
            else:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.debug("Shutting down Loca coordinator")
        await self.api.close()