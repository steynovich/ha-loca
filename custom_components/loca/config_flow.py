"""Config flow for Loca Device Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client

from .api import LocaAPI
from .const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME, DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = LocaAPI(
        data[CONF_API_KEY], 
        data[CONF_USERNAME], 
        data[CONF_PASSWORD],
        aiohttp_client.async_get_clientsession(hass),
    )
    
    try:
        # Test authentication
        auth_success = await api.authenticate()
        if not auth_success:
            raise InvalidAuth("Authentication failed")
        
        # Try to get assets (but don't fail if none found)
        assets = await api.get_assets()
        _LOGGER.info("Authentication successful. Found %d devices.", len(assets) if assets else 0)
        
        # Note: Empty assets list is acceptable - user might not have devices yet
        _LOGGER.info("Config flow validation successful for user: %s", data[CONF_USERNAME])
            
    except InvalidAuth:
        # Re-raise authentication errors
        _LOGGER.error("Authentication validation failed for user: %s", data[CONF_USERNAME])
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected exception during validation for user '%s': %s", data[CONF_USERNAME], err)
        raise CannotConnect from err
    
    finally:
        await api.close()
    
    # Return info that you want to store in the config entry.
    return {"title": f"Loca ({data[CONF_USERNAME]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Loca Device Tracker."""

    VERSION = 1
    _reauth_entry: ConfigEntry | None = None

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate new credentials
                await validate_input(self.hass, user_input)
                
                # Update the existing config entry
                if self._reauth_entry is not None:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry, data=user_input
                    )
                    
                    # Reload the config entry to apply new credentials
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                
                return self.async_abort(reason="reauth_successful")
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauthentication")
                errors["base"] = "unknown"

        # Pre-fill form with existing data (except password)
        existing_data = self._reauth_entry.data if self._reauth_entry is not None else {}
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=existing_data.get(CONF_API_KEY, "")): str,
                vol.Required(CONF_USERNAME, default=existing_data.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"username": existing_data.get(CONF_USERNAME, "")},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a options flow for Loca."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            # Update the config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Get current options or defaults
        current_scan_interval = self.config_entry.options.get(
            "scan_interval", DEFAULT_SCAN_INTERVAL
        )
        
        data_schema = vol.Schema({
            vol.Optional(
                "scan_interval",
                default=current_scan_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )