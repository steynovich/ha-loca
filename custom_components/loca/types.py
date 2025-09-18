"""Type definitions for Loca integration."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict, Protocol, Any

# Literal types for better type safety
LocationSource = Literal["GPS", "Cell Tower"]
AssetType = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
SensorType = Literal["battery", "last_seen", "location_accuracy", "asset_info", "speed", "location_update", "location"]


class AssetInfo(TypedDict, total=False):
    """Type definition for asset information."""
    brand: str
    model: str
    serial: str
    type: AssetType
    group_id: int
    group_name: str


class AddressDetails(TypedDict, total=False):
    """Type definition for address details."""
    street: str
    number: str
    city: str
    district: str
    region: str
    state: str
    zipcode: str
    country: str


class LocationUpdate(TypedDict, total=False):
    """Type definition for location update configuration."""
    frequency: int
    always: int
    begin: int
    end: int
    timeofday: int


class DeviceData(TypedDict):
    """Type definition for device data."""
    device_id: str
    name: str
    latitude: float
    longitude: float
    battery_level: int | None
    gps_accuracy: int
    last_seen: datetime | None
    location_source: LocationSource
    address: str | None
    location_label: str | None
    speed: float
    satellites: int
    signal_strength: int
    asset_info: AssetInfo
    location_update: LocationUpdate
    address_details: AddressDetails
    attributes: dict[str, Any]


class APIResponse(Protocol):
    """Protocol for API response objects."""
    status: int

    async def json(self) -> dict[str, Any]:
        """Return JSON response data."""
        ...

    async def text(self) -> str:
        """Return text response data."""
        ...


class ConfigData(TypedDict):
    """Type definition for configuration data."""
    api_key: str
    username: str
    password: str


class APICredentials(TypedDict):
    """Type definition for API credentials."""
    key: str
    username: str
    password: str


class StatusEntry(TypedDict, total=False):
    """Type definition for status list entry."""
    Asset: dict[str, Any]
    History: dict[str, Any]
    Spot: dict[str, Any]


class LocationEntry(TypedDict, total=False):
    """Type definition for location list entry."""
    id: str | int
    label: str
    latitude: float | str
    longitude: float | str
    radius: int
    street: str
    number: str
    city: str
    zipcode: str
    country: str
    insert: str
    update: str


class ErrorResult(TypedDict):
    """Type definition for error results."""
    base: Literal["cannot_connect", "invalid_auth", "unknown"]