"""Diagnostics support for Loca.

This module provides diagnostic data for troubleshooting while ensuring
sensitive information (API keys, passwords, exact coordinates) is properly
masked or excluded for security and privacy protection.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data
    
    # Gather coordinator data (mask sensitive information)
    diagnostics_data: dict[str, Any] = {
        "config_entry": {
            "title": config_entry.title,
            "domain": config_entry.domain,
            "version": config_entry.version,
            "unique_id": config_entry.unique_id,
            "state": config_entry.state.value,
            "source": config_entry.source,
            # Mask sensitive configuration data
            "data_keys": list(config_entry.data.keys()),
            "api_key": "**REDACTED**" if "api_key" in config_entry.data else None,
            "username": "**REDACTED**" if "username" in config_entry.data else None,
            "password": "**REDACTED**" if "password" in config_entry.data else None,
            "options": dict(config_entry.options) if config_entry.options else {},
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
            "device_count": len(coordinator.data) if coordinator.data else 0,
        },
        "api_info": {
            "authenticated": coordinator.api.is_authenticated,
            "base_url": "https://api.loca.nl/v1",  # Static, non-sensitive URL
            "endpoints_used": [
                "Login.json",
                "Logout.json",
                "Assets.json",
                "StatusList.json",
                "Groups.json",
            ],
            # Don't expose actual API credentials - only indicate if they're configured
            "credentials_configured": coordinator.api.has_credentials,
            "groups_cache_size": coordinator.api.groups_cache_size,
        },
    }
    
    # Add device information (include all data for diagnostics)
    if coordinator.data:
        devices_info = []
        for device_id, device_data in coordinator.data.items():
            # Include device data with privacy-sensitive information redacted
            device_info = {
                "device_id": device_id,
                "name": device_data.get("name", "Unknown"),
                "battery_level": device_data.get("battery_level"),
                "latitude": "**REDACTED**" if device_data.get("latitude") is not None else None,
                "longitude": "**REDACTED**" if device_data.get("longitude") is not None else None,
                "has_gps_data": device_data.get("latitude") is not None and device_data.get("longitude") is not None,
                "gps_accuracy": device_data.get("gps_accuracy"),
                "last_seen": device_data.get("last_seen").isoformat() if device_data.get("last_seen") else None,
                "asset_info": device_data.get("asset_info"),
            }
            devices_info.append(device_info)
        
        diagnostics_data["devices"] = devices_info
    
    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    coordinator = config_entry.runtime_data
    
    # Find the device ID from device identifiers
    device_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            device_id = identifier[1]
            break
    
    if not coordinator or not coordinator.data:
        return {}
    
    if not device_id or device_id not in coordinator.data:
        return {}
    
    device_data = coordinator.data[device_id]
    
    # Return device data with sensitive location information redacted
    return {
        "device_id": device_id,
        "name": device_data.get("name", "Unknown"),
        "battery_level": device_data.get("battery_level"),
        "latitude": "**REDACTED**" if device_data.get("latitude") is not None else None,
        "longitude": "**REDACTED**" if device_data.get("longitude") is not None else None,
        "has_gps_data": device_data.get("latitude") is not None and device_data.get("longitude") is not None,
        "gps_accuracy": device_data.get("gps_accuracy"),
        "last_seen": device_data.get("last_seen").isoformat() if device_data.get("last_seen") else None,
        "asset_info": device_data.get("asset_info"),
        "address": "**REDACTED**" if device_data.get("address") else None,
        "speed": device_data.get("speed"),
        "heading": device_data.get("heading"),
        "altitude": device_data.get("altitude"),
        "group_name": device_data.get("group_name"),
        "is_online": device_data.get("is_online"),
        "motion_state": device_data.get("motion_state"),
    }