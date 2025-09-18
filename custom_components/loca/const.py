"""Constants for the Loca Device Tracker integration."""
from __future__ import annotations

DOMAIN: str = "loca"

# Configuration
CONF_API_KEY: str = "api_key"
CONF_USERNAME: str = "username"
CONF_PASSWORD: str = "password"

# API
API_BASE_URL: str = "https://api.loca.nl/v1"
API_LOGIN_ENDPOINT: str = "Login.json"
API_LOGOUT_ENDPOINT: str = "Logout.json"
API_ASSETS_ENDPOINT: str = "Assets.json"
API_LOCATIONS_ENDPOINT: str = "UserLocationList.json"
API_STATUS_ENDPOINT: str = "StatusList.json"
API_GROUPS_ENDPOINT: str = "Groups.json"

# Update intervals
DEFAULT_SCAN_INTERVAL: int = 60  # seconds

# HTTP Status Codes
class HTTPStatus:
    """HTTP status codes used in the integration."""
    OK = 200
    FORBIDDEN = 403
    NOT_FOUND = 404
    UNAUTHORIZED = 401

# Time Constants
class TimeConstants:
    """Time conversion constants."""
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    HOURS_PER_DAY = 24
    MINUTES_PER_HOUR = 60

# API Response Constants
class APIConstants:
    """Constants for API responses and error handling."""
    ERROR_FIELDS = ["message", "error", "description", "detail", "reason"]
    CONNECTIVITY_TEST_ERRORS = [
        "cannot connect to host",
        "name or service not known",
        "ssl",
        "certificate",
        "timeout",
    ]
    AUTH_ERROR_TERMS = ["auth", "401", "403", "unauthorized", "forbidden"]

# Location Constants
class LocationConstants:
    """Constants for location processing."""
    GPS_ORIGIN_TYPE = 1
    CELL_TOWER_ORIGIN_TYPE = 2
    GPS_SOURCE_NAME = "GPS"
    CELL_TOWER_SOURCE_NAME = "Cell Tower"
    DEFAULT_GPS_ACCURACY = 100
    MIN_LATITUDE = -90
    MAX_LATITUDE = 90
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180

# Device attributes
ATTR_BATTERY_LEVEL: str = "battery_level"
ATTR_GPS_ACCURACY: str = "gps_accuracy"
ATTR_LAST_SEEN: str = "last_seen"
ATTR_DEVICE_TYPE: str = "device_type"
ATTR_SIGNAL_STRENGTH: str = "signal_strength"

# Loca asset type to Home Assistant icon mapping
LOCA_ASSET_TYPE_ICONS: dict[int, str] = {
    0: "mdi:radar",  # Loca (generic tracking device)
    1: "mdi:car",  # Car
    2: "mdi:bicycle",  # Bike
    3: "mdi:sail-boat",  # Boat
    4: "mdi:truck-trailer",  # Cargo Trailer
    5: "mdi:package-variant-closed",  # Container
    6: "mdi:delete-variant",  # Dumpster
    7: "mdi:excavator",  # Excavator
    8: "mdi:engine",  # Generator
    9: "mdi:motorcycle",  # Motorbike
    10: "mdi:scooter-electric",  # Scooter
    11: "mdi:briefcase",  # Suitcase
    12: "mdi:truck",  # Truck
    13: "mdi:trailer",  # Utility Trailer
    14: "mdi:van-utility",  # Van
}