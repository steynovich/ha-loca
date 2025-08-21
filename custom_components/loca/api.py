"""API client for Loca devices."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import (
    API_ASSETS_ENDPOINT,
    API_BASE_URL,
    API_LOGIN_ENDPOINT,
    API_LOGOUT_ENDPOINT,
    API_LOCATIONS_ENDPOINT,
    API_STATUS_ENDPOINT,
    API_GROUPS_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class LocaAPI:
    """Class to communicate with the Loca API."""

    def __init__(
        self, 
        api_key: str, 
        username: str, 
        password: str, 
        hass: HomeAssistant | None = None,
        session: ClientSession | None = None
    ) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._username = username
        self._password = password
        self._hass = hass
        self._session: ClientSession | None = session
        self._authenticated = False
        self._groups_cache: dict[int, str] = {}

    async def _get_session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            if self._hass:
                # Use Home Assistant's shared session when available
                self._session = aiohttp_client.async_get_clientsession(self._hass)
            else:
                # Fallback for testing or standalone use
                timeout = ClientTimeout(total=30)
                jar = aiohttp.CookieJar(unsafe=True)
                self._session = ClientSession(
                    timeout=timeout,
                    cookie_jar=jar,
                    headers={"Content-Type": "application/json"},
                )
        return self._session

    async def authenticate(self) -> bool:
        """Authenticate with the Loca API."""
        # Validate required credentials
        if not self._api_key or not self._username or not self._password:
            _LOGGER.error("Missing required credentials - API key: %s, Username: %s, Password: %s", 
                         bool(self._api_key), bool(self._username), bool(self._password))
            return False
        
        session = await self._get_session()
        
        login_data = {
            "key": self._api_key,
            "username": self._username,
            "password": self._password,
        }
        
        _LOGGER.debug("Attempting authentication for user '%s' with API key length %d", self._username, len(self._api_key))
        
        try:
            # First test basic connectivity to the API endpoint
            try:
                async with session.get(API_BASE_URL.replace('/v1', '')) as test_response:
                    _LOGGER.debug("API server connectivity test - Status: %s", test_response.status)
            except Exception as connectivity_err:
                _LOGGER.warning("API connectivity test failed: %s", connectivity_err)
            
            async with session.post(
                f"{API_BASE_URL}/{API_LOGIN_ENDPOINT}",
                json=login_data,
            ) as response:
                _LOGGER.debug("Authentication request to %s returned status %s", f"{API_BASE_URL}/{API_LOGIN_ENDPOINT}", response.status)
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        _LOGGER.debug("Authentication response data keys: %s", list(data.keys()) if isinstance(data, dict) else "Not a dict")
                        
                        # Loca API returns a 'user' object on successful login (no 'status' field)
                        if data.get("user") and isinstance(data.get("user"), dict):
                            user_info = data["user"]
                            self._authenticated = True
                            _LOGGER.info("Successfully authenticated with Loca API for user: %s (ID: %s)", 
                                        user_info.get("username", self._username), 
                                        user_info.get("userid", "unknown"))
                            return True
                        else:
                            # No user object found - authentication failed
                            _LOGGER.error("Authentication failed for user '%s' - No user object in response. Full response: %s", self._username, data)
                            
                            # Check for error fields
                            error_detail = None
                            for field in ["message", "error", "description", "detail", "reason"]:
                                if data.get(field):
                                    error_detail = data.get(field)
                                    break
                            
                            if error_detail:
                                _LOGGER.error("API error message: %s", error_detail)
                            
                            return False
                    except Exception as json_err:
                        response_text = await response.text()
                        _LOGGER.error("Failed to parse JSON response for user '%s'. Error: %s, Response: %s", self._username, json_err, response_text[:200])
                        return False
                else:
                    try:
                        error_text = await response.text()
                        _LOGGER.error("Authentication failed for user '%s' with HTTP status %s: %s", self._username, response.status, error_text[:200])
                    except Exception:
                        _LOGGER.error("Authentication failed for user '%s' with HTTP status %s (could not read response)", self._username, response.status)
                    return False
                    
        except Exception as err:
            _LOGGER.exception("Network or connection error during authentication for user '%s': %s", self._username, err)
            # Provide specific error messages for common issues
            error_str = str(err).lower()
            if "cannot connect to host" in error_str or "name or service not known" in error_str:
                _LOGGER.error("Cannot connect to Loca API server. Check internet connection and API endpoint: %s", API_BASE_URL)
            elif "ssl" in error_str or "certificate" in error_str:
                _LOGGER.error("SSL/TLS error connecting to Loca API. This might be a certificate issue.")
            elif "timeout" in error_str:
                _LOGGER.error("Timeout connecting to Loca API. Check internet connection and firewall settings.")
            elif "403" in error_str or "forbidden" in error_str:
                _LOGGER.error("Access forbidden by Loca API. Check your API key permissions.")
            elif "404" in error_str:
                _LOGGER.error("Loca API endpoint not found. API might be down or URL incorrect: %s/%s", API_BASE_URL, API_LOGIN_ENDPOINT)
            return False

    async def logout(self) -> bool:
        """Logout from the Loca API."""
        if not self._authenticated:
            return True
            
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_LOGOUT_ENDPOINT}",
                json={"key": self._api_key},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "ok":
                        self._authenticated = False
                        _LOGGER.info("Successfully logged out from Loca API")
                        return True
                    else:
                        _LOGGER.error("Logout failed: %s", data.get("message", "Unknown error"))
                        return False
                else:
                    _LOGGER.error("Logout failed with status: %s", response.status)
                    return False
                    
        except Exception as err:
            _LOGGER.exception("Error during logout: %s", err)
            return False

    async def get_assets(self) -> list[dict[str, Any]]:
        """Get all assets (devices) from the Loca API."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_ASSETS_ENDPOINT}",
                json={"key": self._api_key},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Assets response data keys: %s", list(data.keys()) if isinstance(data, dict) else "Not a dict")
                    _LOGGER.debug("Full Assets response structure: %s", data)
                    
                    # Check for direct assets array or nested structure
                    assets = None
                    if isinstance(data, list):
                        # Response is directly an array of assets
                        assets = data
                    elif isinstance(data, dict) and "assets" in data:
                        # Response has assets field (with status="ok" format)
                        assets = data.get("assets", [])
                    elif isinstance(data, dict) and any(key.isdigit() or "asset" in key.lower() for key in data.keys()):
                        # Response might be a dict of assets
                        assets = list(data.values()) if all(isinstance(v, dict) for v in data.values()) else []
                    
                    if assets is not None:
                        _LOGGER.info("Successfully retrieved %s assets from Loca API", len(assets))
                        if not assets:
                            _LOGGER.info("No devices found in Loca account - this is normal for new accounts")
                        return assets
                    else:
                        status = data.get("status", "no status field")
                        error_detail = None
                        
                        # Check for various error message fields
                        for field in ["message", "error", "description", "detail", "reason"]:
                            if data.get(field):
                                error_detail = data.get(field)
                                break
                        
                        if not error_detail:
                            error_detail = f"API returned status='{status}'. Full response: {data}"
                        
                        _LOGGER.error("Assets request failed - API Status: '%s', Error: %s", status, error_detail)
                        return []
                else:
                    _LOGGER.error("Failed to get assets with status: %s", response.status)
                    return []
                    
        except Exception as err:
            _LOGGER.exception("Error getting assets: %s", err)
            return []

    async def get_user_locations(self) -> list[dict[str, Any]]:
        """Get user-defined locations from the Loca API."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_LOCATIONS_ENDPOINT}",
                json={"key": self._api_key},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Locations response data type: %s", type(data))
                    
                    # UserLocationList.json returns a direct array of location objects
                    if isinstance(data, list):
                        # Response is directly an array of locations (primary format)
                        locations = data
                        _LOGGER.debug("Retrieved %s user locations from direct array", len(locations))
                        return locations
                    elif isinstance(data, dict):
                        # Check for nested response format: response.UserLocationList (fallback)
                        if data.get("response") and isinstance(data["response"], dict):
                            response_obj = data["response"]
                            if "UserLocationList" in response_obj:
                                locations = response_obj["UserLocationList"]
                                if isinstance(locations, list):
                                    _LOGGER.debug("Retrieved %s user locations from response.UserLocationList", len(locations))
                                    return locations
                        
                        # Check if it's wrapped in a status response (fallback)
                        if data.get("status") == "ok" and data.get("locations"):
                            locations = data.get("locations", [])
                            _LOGGER.debug("Retrieved %s user locations from wrapped response", len(locations))
                            return locations
                        
                        # Check for direct locations field (fallback)  
                        if data.get("locations") and isinstance(data["locations"], list):
                            locations = data["locations"]
                            _LOGGER.debug("Retrieved %s user locations from direct locations field", len(locations))
                            return locations
                        
                        # Check for error in dict response
                        error_detail = None
                        for field in ["message", "error", "description", "detail", "reason"]:
                            if data.get(field):
                                error_detail = data.get(field)
                                break
                        
                        if error_detail:
                            _LOGGER.error("Failed to get locations: %s", error_detail)
                        else:
                            _LOGGER.error("Unexpected locations response format: %s", data)
                        return []
                    else:
                        _LOGGER.error("Unexpected locations response type: %s", type(data))
                        return []
                else:
                    _LOGGER.error("Failed to get locations with status: %s", response.status)
                    return []
                    
        except Exception as err:
            _LOGGER.exception("Error getting locations: %s", err)
            return []

    async def get_status_list(self) -> list[dict[str, Any]]:
        """Get device status data from the StatusList API."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_STATUS_ENDPOINT}",
                json={"key": self._api_key},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("StatusList response data type: %s", type(data))
                    _LOGGER.debug("Full StatusList response structure: %s", data)
                    
                    # StatusList.json returns data nested under StatusList key
                    if isinstance(data, list):
                        # Response is directly an array of status entries (fallback)
                        _LOGGER.debug("Retrieved %s status entries from direct array", len(data))
                        return data
                    elif isinstance(data, dict):
                        # Check for the actual Loca API format: StatusList key
                        if "StatusList" in data and isinstance(data["StatusList"], list):
                            status_list = data["StatusList"]
                            _LOGGER.debug("Retrieved %s status entries from StatusList key", len(status_list))
                            return status_list
                        
                        # Check for various other possible response structures (fallbacks)
                        if data.get("status") == "ok" and data.get("devices"):
                            devices = data.get("devices", [])
                            _LOGGER.debug("Retrieved %s status entries from wrapped response", len(devices))
                            return devices
                        
                        # Check for direct devices field
                        if data.get("devices") and isinstance(data["devices"], list):
                            devices = data["devices"]
                            _LOGGER.debug("Retrieved %s status entries from devices field", len(devices))
                            return devices
                        
                        # Check for error in dict response
                        error_detail = None
                        for field in ["message", "error", "description", "detail", "reason"]:
                            if data.get(field):
                                error_detail = data.get(field)
                                break
                        
                        if error_detail:
                            _LOGGER.error("Failed to get status list: %s", error_detail)
                        else:
                            _LOGGER.error("Unexpected StatusList response format: %s", data)
                        return []
                    else:
                        _LOGGER.error("Unexpected StatusList response type: %s", type(data))
                        return []
                else:
                    _LOGGER.error("Failed to get status list with status: %s", response.status)
                    return []
                    
        except Exception as err:
            _LOGGER.exception("Error getting status list: %s", err)
            return []

    async def get_groups(self) -> list[dict[str, Any]]:
        """Get groups from the Loca API."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_GROUPS_ENDPOINT}",
                json={"key": self._api_key},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Groups response data type: %s", type(data))
                    _LOGGER.debug("Full Groups response structure: %s", data)
                    
                    # Groups.json returns data with groups key
                    if isinstance(data, dict) and "groups" in data:
                        groups = data["groups"]
                        if isinstance(groups, list):
                            _LOGGER.debug("Retrieved %s groups", len(groups))
                            return groups
                    elif isinstance(data, list):
                        # Response is directly an array of groups (fallback)
                        _LOGGER.debug("Retrieved %s groups from direct array", len(data))
                        return data
                    
                    # Check for error in response
                    error_detail = None
                    for field in ["message", "error", "description", "detail", "reason"]:
                        if data.get(field):
                            error_detail = data.get(field)
                            break
                    
                    if error_detail:
                        _LOGGER.error("Failed to get groups: %s", error_detail)
                    else:
                        _LOGGER.error("Unexpected Groups response format: %s", data)
                    return []
                else:
                    _LOGGER.error("Failed to get groups with status: %s", response.status)
                    return []
                    
        except Exception as err:
            _LOGGER.exception("Error getting groups: %s", err)
            return []

    async def update_groups_cache(self) -> None:
        """Update the groups cache from the API."""
        groups = await self.get_groups()
        self._groups_cache.clear()
        for group in groups:
            group_id = group.get("id")
            group_label = group.get("label", "")
            if group_id is not None:
                self._groups_cache[int(group_id)] = group_label
        _LOGGER.debug("Updated groups cache with %s groups", len(self._groups_cache))

    def get_group_name(self, group_id: int | None) -> str:
        """Get group name from cache by group ID."""
        if group_id is None:
            return ""
        return self._groups_cache.get(int(group_id), "")

    def parse_status_as_device(self, status_entry: dict[str, Any]) -> dict[str, Any]:
        """Parse status data from StatusList as device data."""
        # Extract Asset information
        asset = status_entry.get("Asset", {})
        device_id = str(asset.get("id", ""))
        name = asset.get("label", f"Loca Device {device_id}")
        
        # Extract History (actual GPS) data
        history = status_entry.get("History", {})
        
        # Extract Spot (processed location) data for address info
        spot = status_entry.get("Spot", {})
        
        _LOGGER.debug("Parsing StatusList entry for device %s: Asset=%s, History=%s, Spot=%s", 
                     device_id, asset, history, spot)
        
        # Get GPS coordinates from History (real-time GPS data)
        latitude = float(history.get("latitude", 0))
        longitude = float(history.get("longitude", 0))
        
        # Parse timestamp from History
        timestamp = history.get("time", 0)
        last_seen = None
        if timestamp:
            try:
                from datetime import timezone
                last_seen = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            except (ValueError, TypeError) as e:
                _LOGGER.debug("Could not parse timestamp %s: %s", timestamp, e)
        
        # Get battery level from History (charge field)
        battery_level = history.get("charge")
        if battery_level is not None:
            battery_level = int(float(battery_level))
        
        # Get GPS quality info
        gps_accuracy = history.get("HDOP", 1)  # HDOP as accuracy indicator
        satellites = history.get("SATU", 0)  # Number of satellites
        signal_strength = history.get("strength", 0)  # GSM signal strength
        speed = history.get("speed", 0.0)  # Current speed
        
        # Get origin type (1=GPS, 2=LBS)
        origin_type = spot.get("origin", 1) if spot else 1
        location_source = "GPS" if origin_type == 1 else "Cell Tower"
        
        # Build address from Spot data using Dutch formatting conventions
        # Dutch format: "Street Number, Zipcode City, Country"
        address_parts = []
        if spot:
            # Street and number (e.g., "Brouwerstraat 30")
            if spot.get("street") and spot.get("number"):
                address_parts.append(f"{spot['street']} {spot['number']}")
            elif spot.get("street"):
                address_parts.append(spot["street"])
            
            # Zipcode and city (e.g., "2984AR Ridderkerk") 
            zipcode_city = []
            if spot.get("zipcode"):
                zipcode_city.append(spot["zipcode"])
            if spot.get("city"):
                zipcode_city.append(spot["city"])
            
            if zipcode_city:
                address_parts.append(" ".join(zipcode_city))
            
            # Country (e.g., "Netherlands")
            if spot.get("country"):
                address_parts.append(spot["country"])
        
        address = ", ".join(address_parts) if address_parts else None
        
        # Use spot label if available, otherwise asset label
        if spot and spot.get("label"):
            location_label = spot["label"]
        else:
            location_label = None
        
        return {
            "device_id": device_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "battery_level": battery_level,
            "gps_accuracy": int(gps_accuracy) if gps_accuracy else 100,
            "last_seen": last_seen,
            "location_source": location_source,
            "address": address,
            "location_label": location_label,
            "speed": float(speed),
            "satellites": int(satellites) if satellites else 0,
            "signal_strength": int(signal_strength) if signal_strength else 0,
            "asset_info": {
                "brand": asset.get("brand", ""),
                "model": asset.get("model", ""),
                "serial": asset.get("serial", ""),
                "type": asset.get("type", 0),
                "group_id": asset.get("group", 0),
                "group_name": self.get_group_name(asset.get("group")),
            },
            "location_update": asset.get("locationupdate", {}),
            "address_details": {
                "street": spot.get("street", "") if spot else "",
                "number": spot.get("number", "") if spot else "",
                "city": spot.get("city", "") if spot else "",
                "district": spot.get("district", "") if spot else "",
                "region": spot.get("region", "") if spot else "",
                "state": spot.get("state", "") if spot else "",
                "zipcode": spot.get("zipcode", "") if spot else "",
                "country": spot.get("country", "") if spot else "",
            },
            "attributes": status_entry,
        }

    def parse_location_as_device(self, location: dict[str, Any]) -> dict[str, Any]:
        """Parse location data from UserLocationList as device data."""
        device_id = str(location.get("id", ""))
        name = location.get("label", f"Loca Location {device_id}")
        
        _LOGGER.debug("Parsing location as device: %s", location)
        
        # Get coordinates from location data
        latitude = float(location.get("latitude", 0))
        longitude = float(location.get("longitude", 0))
        
        # Parse timestamps
        insert_time = location.get("insert", "")
        update_time = location.get("update", "")
        
        # Use the most recent timestamp as last_seen
        last_seen = None
        if update_time:
            try:
                # Handle various datetime formats
                if update_time.endswith("Z"):
                    update_time = update_time.replace("Z", "+00:00")
                elif "+" not in update_time and "T" in update_time:
                    # Assume UTC if no timezone specified
                    update_time += "+00:00"
                last_seen = datetime.fromisoformat(update_time)
            except ValueError:
                _LOGGER.debug("Could not parse update time: %s", update_time)
        
        # Create address string using Dutch formatting conventions
        # Dutch format: "Street Number, Zipcode City, Country"
        address_parts = []
        
        # Street and number (e.g., "Brouwerstraat 30")
        if location.get("street") and location.get("number"):
            address_parts.append(f"{location['street']} {location['number']}")
        elif location.get("street"):
            address_parts.append(location["street"])
        
        # Zipcode and city (e.g., "2984AR Ridderkerk")
        zipcode_city = []
        if location.get("zipcode"):
            zipcode_city.append(location["zipcode"])
        if location.get("city"):
            zipcode_city.append(location["city"])
        
        if zipcode_city:
            address_parts.append(" ".join(zipcode_city))
        
        # Country (e.g., "Netherlands")
        if location.get("country"):
            address_parts.append(location["country"])
        
        address = ", ".join(address_parts) if address_parts else None
        
        return {
            "device_id": device_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "battery_level": None,  # Location entries don't have battery info
            "gps_accuracy": int(location.get("radius", 100)),  # Use radius as accuracy
            "last_seen": last_seen,
            "location_source": "GPS",  # Assume GPS for user locations
            "address": address,
            "attributes": location,
        }

    def parse_device_data(self, asset: dict[str, Any]) -> dict[str, Any]:
        """Parse device data from API response."""
        device_id = str(asset.get("id", ""))
        name = asset.get("name", f"Loca Device {device_id}")
        
        # Debug logging to understand API response structure
        _LOGGER.debug("Raw asset data for device %s: %s", device_id, asset)
        
        # Get the latest location data - try different possible field names
        location_data = asset.get("lastlocation", {})
        if not location_data:
            # Try alternative field names
            location_data = asset.get("last_location", {})
        if not location_data:
            location_data = asset.get("location", {})
        if not location_data:
            # Maybe location data is directly in the asset
            if asset.get("lat") or asset.get("latitude"):
                location_data = asset
        
        _LOGGER.debug("Location data for device %s: %s", device_id, location_data)
        
        # Try multiple field name variations for latitude/longitude
        latitude = 0.0
        longitude = 0.0
        
        # Check for lat/lng
        if location_data.get("lat"):
            latitude = float(location_data.get("lat", 0))
        elif location_data.get("latitude"):
            latitude = float(location_data.get("latitude", 0))
            
        if location_data.get("lng"):
            longitude = float(location_data.get("lng", 0))
        elif location_data.get("lon"):
            longitude = float(location_data.get("lon", 0))
        elif location_data.get("longitude"):
            longitude = float(location_data.get("longitude", 0))
        
        _LOGGER.debug("Parsed coordinates for device %s: lat=%s, lng=%s", device_id, latitude, longitude)
        
        # Parse timestamp
        timestamp = location_data.get("time", 0)
        if timestamp:
            last_seen = datetime.fromtimestamp(int(timestamp))
        else:
            last_seen = None
        
        # Get device attributes
        battery_level = asset.get("battery", 0)
        gps_accuracy = location_data.get("accuracy", 0)
        origin_type = location_data.get("origin", 1)  # 1=GPS, 2=LBS
        
        return {
            "device_id": device_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "battery_level": int(battery_level) if battery_level else None,
            "gps_accuracy": int(gps_accuracy) if gps_accuracy else 100,  # Default 100m accuracy
            "last_seen": last_seen,
            "location_source": "GPS" if origin_type == 1 else "Cell Tower",
            "attributes": asset,
        }

    async def close(self) -> None:
        """Close the API session."""
        # Logout first if authenticated
        if self._authenticated:
            await self.logout()
            
        # Don't close the session if it's managed by Home Assistant
        if self._session and not self._hass:
            await self._session.close()
            self._session = None
        self._authenticated = False