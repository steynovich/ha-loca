"""DataUpdateCoordinator for Loca."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, NoReturn

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LocaAPI
from .const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EMPTY_DEVICE_THRESHOLD,
    APIConstants,
)
from .error_handling import LocaAPIUnavailableError
from .repairs import (
    async_create_api_auth_issue,
    async_create_no_devices_issue,
    async_delete_api_auth_issue,
    async_delete_no_devices_issue,
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
            await self._ensure_authenticated()
            await self.api.update_groups_cache()

            status_list = await self.api.get_status_list()
            _LOGGER.debug(
                "Fetched %s status entries from StatusList",
                len(status_list) if status_list else 0,
            )

            if not status_list:
                self._handle_empty_status_list()
                return {}

            return self._build_devices_from_status(status_list)

        except ConfigEntryAuthFailed:
            # Re-raise auth errors to trigger reauth flow
            raise
        except LocaAPIUnavailableError as err:
            # Handle API unavailability gracefully - already logged in API layer
            raise UpdateFailed(
                f"Loca API temporarily unavailable: {err.message}"
            ) from err
        except Exception as err:
            self._classify_and_raise(err)

    async def _ensure_authenticated(self) -> None:
        """Authenticate if not already authenticated, else raise ConfigEntryAuthFailed."""
        if self.api.is_authenticated:
            return
        auth_success = await self.api.authenticate()
        if not auth_success:
            raise ConfigEntryAuthFailed("Authentication failed")

    def _handle_empty_status_list(self) -> None:
        """Handle an empty StatusList response.

        Raises ConfigEntryAuthFailed if the session is no longer authenticated;
        otherwise bumps the empty-run counter and opens a repair issue once the
        threshold is crossed.
        """
        if not self.api.is_authenticated:
            _LOGGER.error("Not authenticated when trying to get status list")
            if self.config_entry is not None:
                async_create_api_auth_issue(self.hass, self.config_entry)
            raise ConfigEntryAuthFailed("Authentication required")

        _LOGGER.info(
            "No devices found in Loca StatusList - account may be empty or devices not configured"
        )
        # Only create repair issue once the empty-run streak crosses the threshold
        self._empty_device_count += 1
        if (
            self._empty_device_count >= EMPTY_DEVICE_THRESHOLD
            and self.config_entry is not None
        ):
            _LOGGER.warning(
                "Empty device list persisted for %d consecutive updates (threshold: %d) - creating repair issue",
                self._empty_device_count,
                EMPTY_DEVICE_THRESHOLD,
            )
            async_create_no_devices_issue(self.hass, self.config_entry)

    def _build_devices_from_status(
        self, status_list: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Parse StatusList entries into device records and emit add/remove logs."""
        devices: dict[str, Any] = {}
        for status_entry in status_list:
            device_data = self.api.parse_status_as_device(status_entry)
            device_id = device_data["device_id"]
            devices[device_id] = device_data

            if self.data and device_id not in self.data:
                _LOGGER.info(
                    "New device discovered: %s (%s)",
                    device_data.get("name", "Unknown"),
                    device_id,
                )

        self._log_removed_devices(set(devices))
        _LOGGER.debug("Updated data for %s devices", len(devices))

        if devices:
            async_delete_api_auth_issue(self.hass)
            async_delete_no_devices_issue(self.hass)
            self._empty_device_count = 0

        return devices

    def _log_removed_devices(self, current_ids: set[str]) -> None:
        """Log any devices present in the previous update but missing from this one."""
        if not self.data:
            return
        for removed_id in set(self.data.keys()) - current_ids:
            device_name = self.data.get(removed_id, {}).get("name", "Unknown")
            _LOGGER.info("Device removed: %s (%s)", device_name, removed_id)

    def _classify_and_raise(self, err: Exception) -> NoReturn:
        """Route a generic exception to ConfigEntryAuthFailed or UpdateFailed."""
        error_str = str(err).lower()
        if any(term in error_str for term in APIConstants.AUTH_ERROR_TERMS):
            if self.config_entry is not None:
                async_create_api_auth_issue(self.hass, self.config_entry)
            raise ConfigEntryAuthFailed(f"Authentication error: {err}") from err
        raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.debug("Shutting down Loca coordinator")
        await self.api.close()
