"""API client for Loca devices."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from typing import Any, cast

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import (
    API_ASSETS_ENDPOINT,
    API_BASE_URL,
    API_GROUPS_ENDPOINT,
    API_LOCATIONS_ENDPOINT,
    API_LOGIN_ENDPOINT,
    API_LOGOUT_ENDPOINT,
    API_STATUS_ENDPOINT,
    API_TIMEOUT,
    HTTPStatus,
)
from .error_handling import (
    LocaAPIUnavailableError,
    is_connectivity_error,
    log_connectivity_error,
    sanitize_for_logging,
)
from .validation import DataValidator

_LOGGER = logging.getLogger(__name__)


class APIResponseHelper:
    """Helper class for processing API responses."""

    @staticmethod
    def extract_error_message(data: dict[str, Any]) -> str | None:
        """Extract error message from API response data."""
        for field in ["message", "error", "description", "detail", "reason"]:
            if data.get(field):
                return data.get(field)
        return None

    @staticmethod
    def format_dutch_address(address_data: dict[str, Any]) -> str | None:
        """Format address using Dutch conventions: Street Number, Zipcode City, Country."""
        address_parts = []

        # Street and number (e.g., "Brouwerstraat 30")
        if address_data.get("street") and address_data.get("number"):
            address_parts.append(f"{address_data['street']} {address_data['number']}")
        elif address_data.get("street"):
            address_parts.append(address_data["street"])

        # Zipcode and city (e.g., "2984AR Ridderkerk")
        zipcode_city = []
        if address_data.get("zipcode"):
            zipcode_city.append(address_data["zipcode"])
        if address_data.get("city"):
            zipcode_city.append(address_data["city"])

        if zipcode_city:
            address_parts.append(" ".join(zipcode_city))

        # Country (e.g., "Netherlands")
        if address_data.get("country"):
            address_parts.append(address_data["country"])

        return ", ".join(address_parts) if address_parts else None

    @staticmethod
    def parse_timestamp(timestamp: Any) -> datetime | None:
        """Parse timestamp from various formats (Unix timestamp or ISO string)."""
        if not timestamp:
            return None

        # Try Unix timestamp first (integer or float)
        if isinstance(timestamp, (int, float)):
            try:
                return datetime.fromtimestamp(int(timestamp), tz=UTC)
            except (ValueError, TypeError, OSError) as e:
                _LOGGER.debug(
                    "Could not parse timestamp %s as Unix timestamp: %s", timestamp, e
                )

        # Try ISO format string
        if isinstance(timestamp, str):
            try:
                # Normalize timezone format
                ts = timestamp
                if ts.endswith("Z"):
                    ts = ts.replace("Z", "+00:00")
                elif "+" not in ts and "T" in ts:
                    # Assume UTC if no timezone specified
                    ts += "+00:00"
                return datetime.fromisoformat(ts)
            except ValueError as e:
                _LOGGER.debug(
                    "Could not parse timestamp %s as ISO format: %s", timestamp, e
                )

            # Last resort: try parsing as Unix timestamp string
            try:
                return datetime.fromtimestamp(int(float(timestamp)), tz=UTC)
            except (ValueError, TypeError, OSError) as e:
                _LOGGER.debug(
                    "Could not parse timestamp %s as numeric string: %s", timestamp, e
                )

        return None

    @staticmethod
    def safe_int_conversion(value: Any, default: int = 0) -> int:
        """Safely convert value to int with fallback."""
        if value is None:
            return default
        try:
            return int(float(value))
        except ValueError, TypeError:
            return default

    @staticmethod
    def safe_float_conversion(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float with fallback."""
        if value is None:
            return default
        try:
            return float(value)
        except ValueError, TypeError:
            return default


class LocaAPI:
    """Class to communicate with the Loca API."""

    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        hass: HomeAssistant | None = None,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._username = username
        self._password = password
        self._hass = hass
        self._session: ClientSession | None = session
        self._session_lock = asyncio.Lock()
        self._authenticated = False
        self._groups_cache: dict[int, str] = {}

    @property
    def is_authenticated(self) -> bool:
        """Return whether the API client is authenticated."""
        return self._authenticated

    @property
    def has_credentials(self) -> bool:
        """Return whether credentials are configured."""
        return bool(self._api_key and self._username)

    @property
    def groups_cache_size(self) -> int:
        """Return the number of groups in cache."""
        return len(self._groups_cache)

    async def _get_session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is not None:
            return self._session

        async with self._session_lock:
            # Double-check after acquiring lock
            if self._session is None:
                if self._hass:
                    # Use Home Assistant's shared session when available
                    self._session = aiohttp_client.async_get_clientsession(self._hass)
                else:
                    # Fallback for testing or standalone use
                    # Note: Caller is responsible for closing this session
                    # SSL verification is enabled by default (verify_ssl=True)
                    timeout = ClientTimeout(total=API_TIMEOUT)
                    self._session = ClientSession(
                        timeout=timeout,
                        headers={"Content-Type": "application/json"},
                        # verify_ssl defaults to True - enforces HTTPS certificate validation
                    )
            return self._session

    def _validate_credentials(self) -> bool:
        """Validate that all required credentials are provided."""
        if not self._api_key or not self._username or not self._password:
            _LOGGER.error(
                "Missing required credentials - API key: %s, Username: %s, Password: %s",
                sanitize_for_logging(self._api_key, show_length=False),
                sanitize_for_logging(self._username, show_length=False),
                sanitize_for_logging(self._password, show_length=False),
            )
            return False
        return True

    async def _test_connectivity(self, session: ClientSession) -> None:
        """Test basic connectivity to the API endpoint."""
        try:
            async with session.get(API_BASE_URL.replace("/v1", "")) as test_response:
                _LOGGER.debug(
                    "API server connectivity test - Status: %s", test_response.status
                )
        except Exception as connectivity_err:
            _LOGGER.warning("API connectivity test failed: %s", connectivity_err)

    def _prepare_login_data(self) -> dict[str, str]:
        """Prepare login data for authentication request."""
        return {
            "key": self._api_key,
            "username": self._username,
            "password": self._password,
        }

    def _process_auth_response(self, data: dict[str, Any]) -> bool:
        """Process authentication response data."""
        # Loca API returns a 'user' object on successful login (no 'status' field)
        if data.get("user") and isinstance(data.get("user"), dict):
            user_info = data["user"]
            self._authenticated = True
            _LOGGER.info(
                "Successfully authenticated with Loca API for user: %s (ID: %s)",
                user_info.get("username", self._username),
                user_info.get("userid", "unknown"),
            )
            return True
        # No user object found - authentication failed
        error_detail = APIResponseHelper.extract_error_message(data)
        if error_detail:
            _LOGGER.error(
                "Authentication failed for user '%s': %s",
                self._username,
                error_detail,
            )
        else:
            _LOGGER.error(
                "Authentication failed for user '%s' - No user object in response",
                self._username,
            )
        return False

    def _handle_auth_error(self, err: Exception) -> None:
        """Handle authentication errors with specific error messages."""
        _LOGGER.exception(
            "Network or connection error during authentication for user '%s': %s",
            self._username,
            err,
        )
        # Provide specific error messages for common issues
        error_str = str(err).lower()
        if (
            "cannot connect to host" in error_str
            or "name or service not known" in error_str
        ):
            _LOGGER.error(
                "Cannot connect to Loca API server. Check internet connection and API endpoint: %s",
                API_BASE_URL,
            )
        elif "ssl" in error_str or "certificate" in error_str:
            _LOGGER.error(
                "SSL/TLS error connecting to Loca API. This might be a certificate issue."
            )
        elif "timeout" in error_str:
            _LOGGER.error(
                "Timeout connecting to Loca API. Check internet connection and firewall settings."
            )
        elif "403" in error_str or "forbidden" in error_str:
            _LOGGER.error(
                "Access forbidden by Loca API. Check your API key permissions."
            )
        elif "404" in error_str:
            _LOGGER.error(
                "Loca API endpoint not found. API might be down or URL incorrect: %s/%s",
                API_BASE_URL,
                API_LOGIN_ENDPOINT,
            )

    async def authenticate(self) -> bool:
        """Authenticate with the Loca API."""
        if not self._validate_credentials():
            return False

        session = await self._get_session()
        login_data = self._prepare_login_data()

        _LOGGER.debug(
            "Attempting authentication for user '%s' with API key length %d",
            self._username,
            len(self._api_key),
        )

        try:
            # Test basic connectivity first
            await self._test_connectivity(session)

            async with asyncio.timeout(API_TIMEOUT):
                async with session.post(
                    f"{API_BASE_URL}/{API_LOGIN_ENDPOINT}",
                    json=login_data,
                ) as response:
                    _LOGGER.debug(
                        "Authentication request to %s returned status %s",
                        f"{API_BASE_URL}/{API_LOGIN_ENDPOINT}",
                        response.status,
                    )

                    if response.status == HTTPStatus.OK:
                        try:
                            data = await response.json()
                            _LOGGER.debug(
                                "Authentication response data keys: %s",
                                list(data.keys())
                                if isinstance(data, dict)
                                else "Not a dict",
                            )
                            return self._process_auth_response(data)
                        except Exception as json_err:
                            response_text = await response.text()
                            _LOGGER.error(
                                "Failed to parse JSON response for user '%s'. Error: %s, Response: %s",
                                self._username,
                                json_err,
                                response_text[:200],
                            )
                            return False
                    else:
                        try:
                            error_text = await response.text()
                            _LOGGER.error(
                                "Authentication failed for user '%s' with HTTP status %s: %s",
                                self._username,
                                response.status,
                                error_text[:200],
                            )
                        except Exception:
                            _LOGGER.error(
                                "Authentication failed for user '%s' with HTTP status %s (could not read response)",
                                self._username,
                                response.status,
                            )
                        return False

        except TimeoutError as err:
            _LOGGER.warning(
                "Authentication request timed out after %s seconds", API_TIMEOUT
            )
            raise LocaAPIUnavailableError("Authentication request timed out") from err
        except Exception as err:
            if is_connectivity_error(err):
                log_connectivity_error(_LOGGER, "Authentication", err)
                raise LocaAPIUnavailableError(
                    f"Cannot connect to Loca API: {err}"
                ) from err
            self._handle_auth_error(err)
            return False

    async def _parse_json_or_log(
        self, response: Any, operation_name: str, *, context: str = ""
    ) -> dict[str, Any] | list[Any] | None:
        """Parse a JSON body, logging and returning None on failure."""
        try:
            return await response.json()
        except Exception as json_err:
            suffix = f" {context}" if context else ""
            _LOGGER.error(
                "Failed to parse JSON from %s%s: %s",
                operation_name,
                suffix,
                json_err,
            )
            return None

    async def _reauth_and_retry(
        self,
        session: ClientSession,
        url: str,
        payload: dict[str, Any],
        operation_name: str,
    ) -> dict[str, Any] | list[Any] | None:
        """Clear auth, re-authenticate, and retry the POST exactly once."""
        self._authenticated = False
        if not await self.authenticate():
            _LOGGER.error("%s: re-authentication failed", operation_name)
            return None
        async with session.post(url, json=payload) as retry_response:
            if retry_response.status == HTTPStatus.OK:
                return await self._parse_json_or_log(
                    retry_response, operation_name, context="after reauth"
                )
            _LOGGER.error(
                "%s failed after reauth with status: %s",
                operation_name,
                retry_response.status,
            )
            return None

    async def _post_and_retry_on_401(
        self, endpoint: str, operation_name: str
    ) -> dict[str, Any] | list[Any] | None:
        """POST to an authenticated endpoint, retrying once on 401/403.

        Ensures the client is authenticated first. If the server responds with
        401 or 403 we assume the session expired server-side, clear our auth
        flag, re-authenticate, and retry the request exactly once.

        Returns the parsed JSON body on HTTP 200. Returns ``None`` for any other
        status code, auth failure, or JSON parse failure (an error is logged).
        Raises ``LocaAPIUnavailableError`` on timeout or connectivity errors so
        the coordinator can raise ``UpdateFailed`` cleanly.
        """
        if not self._authenticated and not await self.authenticate():
            return None

        session = await self._get_session()
        url = f"{API_BASE_URL}/{endpoint}"
        payload = {"key": self._api_key}
        auth_expired_statuses = (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)

        try:
            async with (
                asyncio.timeout(API_TIMEOUT),
                session.post(url, json=payload) as response,
            ):
                if response.status in auth_expired_statuses:
                    _LOGGER.info(
                        "%s got HTTP %s - session may have expired, re-authenticating",
                        operation_name,
                        response.status,
                    )
                    return await self._reauth_and_retry(
                        session, url, payload, operation_name
                    )

                if response.status == HTTPStatus.OK:
                    return await self._parse_json_or_log(response, operation_name)

                _LOGGER.error(
                    "%s failed with status: %s", operation_name, response.status
                )
                return None

        except TimeoutError as err:
            _LOGGER.warning(
                "%s request timed out after %s seconds",
                operation_name,
                API_TIMEOUT,
            )
            raise LocaAPIUnavailableError(
                f"{operation_name} request timed out"
            ) from err
        except Exception as err:
            if is_connectivity_error(err):
                log_connectivity_error(_LOGGER, operation_name, err)
                raise LocaAPIUnavailableError(
                    f"Cannot connect to Loca API: {err}"
                ) from err
            _LOGGER.exception("Error during %s: %s", operation_name, err)
            return None

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
                if response.status == HTTPStatus.OK:
                    data = await response.json()
                    if data.get("status") == "ok":
                        self._authenticated = False
                        _LOGGER.info("Successfully logged out from Loca API")
                        return True
                    _LOGGER.error(
                        "Logout failed: %s", data.get("message", "Unknown error")
                    )
                    return False
                _LOGGER.error("Logout failed with status: %s", response.status)
                return False

        except Exception as err:
            if is_connectivity_error(err):
                log_connectivity_error(_LOGGER, "Logout", err)
            else:
                _LOGGER.exception("Error during logout: %s", err)
            return False

    def _extract_assets(self, data: Any) -> list[dict[str, Any]] | None:
        """Pull an assets list out of a response payload, or None if not found."""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return None
        if "assets" in data:
            return data.get("assets", [])
        # Fallback: dict keyed by id / "asset*" whose values are themselves dicts
        if any(key.isdigit() or "asset" in key.lower() for key in data):
            _LOGGER.debug("Using fallback asset parsing for dict response")
            values = list(data.values())
            if all(isinstance(v, dict) for v in values):
                return cast("list[dict[str, Any]]", values)
            return []
        return None

    def _log_unexpected_response(self, operation: str, data: Any) -> None:
        """Log a response that doesn't match any known shape."""
        if isinstance(data, dict):
            status = data.get("status", "no status field")
            error_detail = (
                APIResponseHelper.extract_error_message(data)
                or f"Unexpected response format (status='{status}')"
            )
            _LOGGER.error("%s request failed: %s", operation, error_detail)
        else:
            _LOGGER.error("Unexpected %s response type: %s", operation, type(data))

    async def get_assets(self) -> list[dict[str, Any]]:
        """Get all assets (devices) from the Loca API."""
        data = await self._post_and_retry_on_401(API_ASSETS_ENDPOINT, "Get assets")
        if data is None:
            return []

        _LOGGER.debug(
            "Assets response data keys: %s",
            list(data.keys()) if isinstance(data, dict) else "Not a dict",
        )

        assets = self._extract_assets(data)
        if assets is None:
            self._log_unexpected_response("Assets", data)
            return []

        _LOGGER.info("Successfully retrieved %s assets from Loca API", len(assets))
        if not assets:
            _LOGGER.info(
                "No devices found in Loca account - this is normal for new accounts"
            )
        return assets

    @staticmethod
    def _extract_list_from_response(
        data: Any, candidates: list[str | tuple[str, str]]
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """Extract a list from a response payload by trying shapes in order.

        ``candidates`` items are either a string (``data[key]``) or a
        ``(parent, child)`` tuple (``data[parent][child]``). Returns
        ``(matched_list, source_description)`` or ``(None, "")`` when nothing
        matched. A direct list payload always wins and bypasses ``candidates``.
        """
        if isinstance(data, list):
            return data, "direct array"
        if not isinstance(data, dict):
            return None, ""

        for candidate in candidates:
            if isinstance(candidate, tuple):
                parent_key, child_key = candidate
                parent = data.get(parent_key)
                if (
                    isinstance(parent, dict)
                    and child_key in parent
                    and isinstance(parent[child_key], list)
                ):
                    return parent[child_key], f"{parent_key}.{child_key}"
                continue
            value = data.get(candidate)
            if isinstance(value, list):
                return value, candidate
        return None, ""

    async def get_user_locations(self) -> list[dict[str, Any]]:
        """Get user-defined locations from the Loca API."""
        data = await self._post_and_retry_on_401(
            API_LOCATIONS_ENDPOINT, "Get locations"
        )
        if data is None:
            return []

        _LOGGER.debug("Locations response data type: %s", type(data))

        locations, source = self._extract_list_from_response(
            data, [("response", "UserLocationList"), "locations"]
        )
        if locations is not None:
            _LOGGER.debug("Retrieved %s user locations from %s", len(locations), source)
            return locations

        self._log_unexpected_response("locations", data)
        return []

    async def get_status_list(self) -> list[dict[str, Any]]:
        """Get device status data from the StatusList API."""
        data = await self._post_and_retry_on_401(API_STATUS_ENDPOINT, "Get status list")
        if data is None:
            return []

        _LOGGER.debug("StatusList response data type: %s", type(data))

        status_list, source = self._extract_list_from_response(
            data, ["StatusList", "devices"]
        )
        if status_list is not None:
            _LOGGER.debug(
                "Retrieved %s status entries from %s", len(status_list), source
            )
            return status_list

        self._log_unexpected_response("StatusList", data)
        return []

    async def get_groups(self) -> list[dict[str, Any]]:
        """Get groups from the Loca API."""
        data = await self._post_and_retry_on_401(API_GROUPS_ENDPOINT, "Get groups")
        if data is None:
            return []

        _LOGGER.debug("Groups response data type: %s", type(data))

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

        if isinstance(data, dict):
            error_detail = APIResponseHelper.extract_error_message(data)
            if error_detail:
                _LOGGER.error("Failed to get groups: %s", error_detail)
            else:
                _LOGGER.error("Unexpected Groups response format")
        else:
            _LOGGER.error("Unexpected Groups response type: %s", type(data))
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

    def _extract_device_basic_info(
        self, status_entry: dict[str, Any]
    ) -> tuple[dict[str, Any], str, str]:
        """Extract basic device information from status entry."""
        asset = status_entry.get("Asset", {})
        device_id = str(asset.get("id", ""))
        name = asset.get("label", f"Loca Device {device_id}")
        return asset, device_id, name

    def _extract_location_data(
        self, history: dict[str, Any]
    ) -> tuple[float, float, datetime | None, int | None]:
        """Extract location and timing data from history."""
        # Use validated coordinates with proper bounds checking
        latitude, longitude = DataValidator.safe_validate_coordinates(
            history.get("latitude"),
            history.get("longitude"),
        )
        last_seen = APIResponseHelper.parse_timestamp(history.get("time"))
        # Use validated battery level with proper clamping
        battery_level = DataValidator.validate_battery_level(history.get("charge"))
        return latitude, longitude, last_seen, battery_level

    def _extract_quality_metrics(
        self, history: dict[str, Any]
    ) -> tuple[int, int, int, float]:
        """Extract GPS and signal quality metrics."""
        # Use validated GPS accuracy with minimum enforcement
        gps_accuracy = DataValidator.validate_gps_accuracy(history.get("HDOP", 1))
        satellites = APIResponseHelper.safe_int_conversion(history.get("SATU"))
        signal_strength = APIResponseHelper.safe_int_conversion(history.get("strength"))
        speed = APIResponseHelper.safe_float_conversion(history.get("speed"))
        return gps_accuracy, satellites, signal_strength, speed

    def parse_status_as_device(self, status_entry: dict[str, Any]) -> dict[str, Any]:
        """Parse status data from StatusList as device data."""
        # Extract basic device information
        asset, device_id, name = self._extract_device_basic_info(status_entry)

        # Extract GPS and location data
        history = status_entry.get("History", {})
        spot = status_entry.get("Spot", {})

        _LOGGER.debug(
            "Parsing StatusList entry for device %s: Asset=%s, History=%s, Spot=%s",
            device_id,
            asset,
            history,
            spot,
        )

        # Extract location and timing data
        latitude, longitude, last_seen, battery_level = self._extract_location_data(
            history
        )

        # Extract quality metrics
        gps_accuracy, satellites, signal_strength, speed = (
            self._extract_quality_metrics(history)
        )

        # Determine location source
        origin_type = spot.get("origin", 1) if spot else 1
        location_source = "GPS" if origin_type == 1 else "Cell Tower"

        # Build address using helper method
        address = APIResponseHelper.format_dutch_address(spot) if spot else None

        # Use spot label if available
        location_label = spot.get("label") if spot else None

        return {
            "device_id": device_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "battery_level": battery_level,
            # gps_accuracy is always a positive int - validate_gps_accuracy clamps
            # to max(1, ...)
            "gps_accuracy": gps_accuracy,
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
        }

    def parse_location_as_device(self, location: dict[str, Any]) -> dict[str, Any]:
        """Parse location data from UserLocationList as device data."""
        device_id = str(location.get("id", ""))
        name = location.get("label", f"Loca Location {device_id}")

        _LOGGER.debug("Parsing location as device: %s", location)

        # Get validated coordinates from location data
        latitude, longitude = DataValidator.safe_validate_coordinates(
            location.get("latitude", 0),
            location.get("longitude", 0),
        )

        # Parse timestamp using consolidated helper
        last_seen = APIResponseHelper.parse_timestamp(location.get("update"))

        # Create address string using consolidated Dutch formatting helper
        address = APIResponseHelper.format_dutch_address(location)

        # Validate GPS accuracy (use radius as accuracy)
        gps_accuracy = DataValidator.validate_gps_accuracy(location.get("radius", 100))

        return {
            "device_id": device_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "battery_level": None,  # Location entries don't have battery info
            "gps_accuracy": gps_accuracy,
            "last_seen": last_seen,
            "location_source": "GPS",  # Assume GPS for user locations
            "address": address,
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
