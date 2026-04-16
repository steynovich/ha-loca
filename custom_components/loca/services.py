"""Loca integration services."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN
from .error_handling import LocaAPIUnavailableError

_LOGGER = logging.getLogger(__name__)

# Rate limiting: minimum seconds between service calls
SERVICE_RATE_LIMIT_SECONDS = 5

SERVICE_REFRESH_DEVICES = "refresh_devices"
SERVICE_FORCE_UPDATE = "force_update"

SERVICE_REFRESH_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): str,
    }
)

SERVICE_FORCE_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)


class _LocaServices:
    """Service handlers with shared rate-limit state.

    Held by `async_setup_services` for the lifetime of the integration so the
    per-entry and per-device rate-limit buckets survive across service calls.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._last_refresh: dict[str, datetime] = {}
        self._last_force_update: dict[str, datetime] = {}

    def _check_rate_limit(
        self,
        key: str,
        bucket: dict[str, datetime],
        translation_key: str,
    ) -> None:
        """Raise ServiceValidationError if `key` was used within the rate limit window."""
        last_called = bucket.get(key)
        if last_called is None:
            return
        elapsed = (dt_util.utcnow() - last_called).total_seconds()
        if elapsed < SERVICE_RATE_LIMIT_SECONDS:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=translation_key,
                translation_placeholders={
                    "seconds": str(SERVICE_RATE_LIMIT_SECONDS - int(elapsed))
                },
            )

    async def async_refresh_devices(self, call: ServiceCall) -> None:
        """Refresh devices from Loca API."""
        try:
            config_entry_ids = await async_extract_config_entry_ids(call)
            if not config_entry_ids:
                raise ServiceValidationError("No Loca config entries found")

            for config_entry_id in config_entry_ids:
                self._check_rate_limit(
                    config_entry_id, self._last_refresh, "rate_limit_refresh"
                )

            refreshed_count = await self._refresh_entries(config_entry_ids)
            if refreshed_count == 0:
                raise ServiceValidationError("No valid Loca config entries to refresh")

        except ServiceValidationError:
            raise
        except LocaAPIUnavailableError as err:
            _LOGGER.warning("Loca API unavailable during refresh: %s", err)
            raise HomeAssistantError(
                "Loca API is temporarily unavailable. Please try again later."
            ) from err
        except UpdateFailed as err:
            _LOGGER.error("Failed to refresh devices: %s", err)
            raise HomeAssistantError(f"Failed to refresh devices: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error refreshing devices: %s", err)
            raise HomeAssistantError(
                f"Unexpected error refreshing devices: {err}"
            ) from err

    async def _refresh_entries(self, config_entry_ids: set[str]) -> int:
        """Request a refresh on every Loca config entry in `config_entry_ids`."""
        now = dt_util.utcnow()
        refreshed_count = 0
        for config_entry_id in config_entry_ids:
            config_entry = self._hass.config_entries.async_get_entry(config_entry_id)
            if not config_entry or config_entry.domain != DOMAIN:
                raise ServiceValidationError(
                    f"Config entry {config_entry_id} not found or not a Loca entry"
                )
            coordinator = config_entry.runtime_data
            await coordinator.async_request_refresh()
            self._last_refresh[config_entry_id] = now
            refreshed_count += 1
            _LOGGER.info("Refreshed devices for config entry: %s", config_entry_id)
        return refreshed_count

    async def async_force_update(self, call: ServiceCall) -> None:
        """Force update a specific device."""
        device_id: str | None = None
        try:
            device_id = call.data["device_id"]
            if not device_id:
                raise ServiceValidationError("Device ID is required")

            self._check_rate_limit(
                device_id, self._last_force_update, "rate_limit_update"
            )

            if not await self._refresh_device(device_id):
                raise ServiceValidationError(
                    f"Device '{device_id}' not found in any Loca config entry"
                )

        except ServiceValidationError:
            raise
        except LocaAPIUnavailableError as err:
            _LOGGER.warning("Loca API unavailable during force update: %s", err)
            raise HomeAssistantError(
                "Loca API is temporarily unavailable. Please try again later."
            ) from err
        except UpdateFailed as err:
            _LOGGER.error("Failed to force update device %s: %s", device_id, err)
            raise HomeAssistantError(f"Failed to force update device: {err}") from err
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error force updating device %s: %s", device_id, err
            )
            raise HomeAssistantError(
                f"Unexpected error force updating device: {err}"
            ) from err

    async def _refresh_device(self, device_id: str) -> bool:
        """Trigger a refresh on the coordinator tracking `device_id`. Returns True if found."""
        for config_entry in self._hass.config_entries.async_entries(DOMAIN):
            coordinator = config_entry.runtime_data
            if coordinator.data and device_id in coordinator.data:
                await coordinator.async_request_refresh()
                self._last_force_update[device_id] = dt_util.utcnow()
                _LOGGER.info("Forced update for device: %s", device_id)
                return True
        return False


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Loca integration."""
    services = _LocaServices(hass)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DEVICES,
        services.async_refresh_devices,
        schema=SERVICE_REFRESH_DEVICES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE,
        services.async_force_update,
        schema=SERVICE_FORCE_UPDATE_SCHEMA,
    )

    _LOGGER.info("Loca services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Loca services."""
    hass.services.async_remove(DOMAIN, SERVICE_REFRESH_DEVICES)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
    _LOGGER.info("Loca services unloaded")
