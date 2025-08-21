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