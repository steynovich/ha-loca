"""Repairs for Loca integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id == "deprecated_yaml_configuration":
        return DeprecatedYamlConfigurationRepairFlow()
    if issue_id == "api_authentication_failed": 
        return ApiAuthenticationFailedRepairFlow()
    if issue_id == "no_devices_found":
        return NoDevicesFoundRepairFlow()
    
    return ConfirmRepairFlow()


class DeprecatedYamlConfigurationRepairFlow(RepairsFlow):
    """Handler for deprecated YAML configuration issue."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={},
        )


class ApiAuthenticationFailedRepairFlow(RepairsFlow):
    """Handler for API authentication failed issue."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Trigger reauthentication flow
            config_entries = self.hass.config_entries.async_entries(DOMAIN)
            if config_entries:
                config_entry = config_entries[0]  # Take first entry
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "reauth", "entry_id": config_entry.entry_id},
                        data=config_entry.data,
                    )
                )
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={},
        )


class NoDevicesFoundRepairFlow(RepairsFlow):
    """Handler for no devices found issue."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            description_placeholders={},
        )


def async_create_issue(
    hass: HomeAssistant,
    issue_id: str,
    translation_key: str,
    translation_placeholders: dict[str, str] | None = None,
    severity: ir.IssueSeverity = ir.IssueSeverity.WARNING,
) -> None:
    """Create a repair issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=severity,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
    )


def async_delete_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Delete a repair issue."""
    ir.async_delete_issue(hass, DOMAIN, issue_id)


def async_create_api_auth_issue(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Create an API authentication issue."""
    async_create_issue(
        hass,
        "api_authentication_failed",
        "api_authentication_failed",
        translation_placeholders={"account": config_entry.title},
        severity=ir.IssueSeverity.ERROR,
    )


def async_create_no_devices_issue(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Create a no devices found issue.""" 
    async_create_issue(
        hass,
        "no_devices_found",
        "no_devices_found",
        translation_placeholders={"account": config_entry.title},
        severity=ir.IssueSeverity.WARNING,
    )


def async_delete_api_auth_issue(hass: HomeAssistant) -> None:
    """Delete API authentication issue."""
    async_delete_issue(hass, "api_authentication_failed")


def async_delete_no_devices_issue(hass: HomeAssistant) -> None:
    """Delete no devices found issue."""
    async_delete_issue(hass, "no_devices_found")