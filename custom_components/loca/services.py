"""Loca integration services."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .error_handling import LocaAPIUnavailableError

_LOGGER = logging.getLogger(__name__)

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


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Loca integration."""
    
    async def async_refresh_devices(call: ServiceCall) -> None:
        """Refresh devices from Loca API."""
        try:
            config_entry_ids = await async_extract_config_entry_ids(call)

            if not config_entry_ids:
                raise ServiceValidationError("No Loca config entries found")

            refreshed_count = 0
            for config_entry_id in config_entry_ids:
                config_entry = hass.config_entries.async_get_entry(config_entry_id)
                if config_entry and config_entry.domain == DOMAIN:
                    coordinator = config_entry.runtime_data
                    await coordinator.async_request_refresh()
                    refreshed_count += 1
                    _LOGGER.info("Refreshed devices for config entry: %s", config_entry_id)
                else:
                    raise ServiceValidationError(f"Config entry {config_entry_id} not found or not a Loca entry")

            if refreshed_count == 0:
                raise ServiceValidationError("No valid Loca config entries to refresh")

        except ServiceValidationError:
            # Re-raise validation errors without wrapping
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
            raise HomeAssistantError(f"Unexpected error refreshing devices: {err}") from err

    async def async_force_update(call: ServiceCall) -> None:
        """Force update a specific device."""
        device_id: str | None = None
        try:
            device_id = call.data["device_id"]

            if not device_id:
                raise ServiceValidationError("Device ID is required")

            # Find the coordinator containing this device
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                coordinator = config_entry.runtime_data
                if coordinator.data and device_id in coordinator.data:
                    await coordinator.async_request_refresh()
                    _LOGGER.info("Forced update for device: %s", device_id)
                    return

            # Device not found in any coordinator
            raise ServiceValidationError(f"Device '{device_id}' not found in any Loca config entry")

        except ServiceValidationError:
            # Re-raise validation errors without wrapping
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
            _LOGGER.exception("Unexpected error force updating device %s: %s", device_id, err)
            raise HomeAssistantError(f"Unexpected error force updating device: {err}") from err

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DEVICES,
        async_refresh_devices,
        schema=SERVICE_REFRESH_DEVICES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE,
        async_force_update,
        schema=SERVICE_FORCE_UPDATE_SCHEMA,
    )

    _LOGGER.info("Loca services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Loca services."""
    hass.services.async_remove(DOMAIN, SERVICE_REFRESH_DEVICES)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
    _LOGGER.info("Loca services unloaded")