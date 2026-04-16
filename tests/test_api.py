"""Tests for Loca API client."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from aiohttp import ClientSession, ClientTimeout
import pytest

from custom_components.loca.api import LocaAPI


@pytest.fixture
def api() -> LocaAPI:
    """Create a test API instance."""
    return LocaAPI("test_api_key", "test_user", "test_password")


@pytest.fixture
def api_with_session() -> LocaAPI:
    """Create a test API instance with hass."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    return LocaAPI("test_api_key", "test_user", "test_password", hass=mock_hass)


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock aiohttp session."""
    session = MagicMock(spec=ClientSession)
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_auth_response() -> dict[str, Any]:
    """Mock successful authentication response."""
    return {
        "user": {
            "userid": 1,
            "id": 1,
            "username": "test_user",
            "email": "test@example.com",
        }
    }


@pytest.fixture
def mock_assets_response() -> dict[str, Any]:
    """Mock successful assets response."""
    return {
        "status": "ok",
        "assets": [
            {
                "id": "12345",
                "name": "Test Device",
                "battery": 85,
                "lastlocation": {
                    "lat": 52.3676,
                    "lng": 4.9041,
                    "time": 1640995200,
                    "accuracy": 5,
                    "origin": 1,
                },
            },
            {
                "id": "67890",
                "name": "Second Device",
                "battery": 42,
                "lastlocation": {
                    "lat": 51.5074,
                    "lng": -0.1278,
                    "time": 1640995260,
                    "accuracy": 10,
                    "origin": 2,
                },
            },
        ],
    }


@pytest.fixture
def mock_status_list_response() -> list[dict[str, Any]]:
    """Mock successful StatusList response."""
    return [
        {
            "Asset": {
                "id": "12345",
                "label": "Test Device",
                "type": 1,
                "brand": "BMW",
                "model": "X3",
                "serial": "ABC123",
            },
            "History": {
                "latitude": 52.3676,
                "longitude": 4.9041,
                "time": 1640995200,
                "charge": 85,
                "HDOP": 5,
                "SATU": 8,
                "speed": 65.5,
                "strength": 75,
            },
            "Spot": {
                "street": "Test Street",
                "number": "42",
                "city": "Amsterdam",
                "zipcode": "1234AB",
                "country": "Netherlands",
                "origin": 1,
            },
        }
    ]


@pytest.fixture
def mock_groups_response() -> dict[str, Any]:
    """Mock successful groups response."""
    return {
        "groups": [
            {"id": 248, "label": "Autos", "account": 2},
            {"id": 276, "label": "Motoren", "account": 2},
        ]
    }


@pytest.fixture
def mock_locations_response() -> list[dict[str, Any]]:
    """Mock successful locations response."""
    return [
        {
            "id": "1",
            "insert": "2022-02-06 09:43:21",
            "update": "2022-04-26 19:35:06",
            "label": "Home",
            "latitude": "51.876682",
            "longitude": "4.615142",
            "number": "30",
            "street": "Brouwerstraat",
            "city": "Ridderkerk",
            "state": "Zuid-Holland",
            "zipcode": "2984AR",
            "country": "Netherlands",
            "radius": "100",
        }
    ]


class TestLocaAPIInitialization:
    """Test API client initialization."""

    def test_init_basic(self, api: LocaAPI) -> None:
        """Test basic initialization."""
        assert api._api_key == "test_api_key"
        assert api._username == "test_user"
        assert api._password == "test_password"
        assert api._session is None
        assert api._authenticated is False
        assert api.is_authenticated is False  # Test public property
        assert api._groups_cache == {}

    def test_init_with_hass(self, api_with_session: LocaAPI) -> None:
        """Test initialization with Home Assistant instance."""
        # Session will be created from hass when needed
        assert api_with_session._hass is not None
        assert api_with_session._session is None  # Not created yet


class TestSessionManagement:
    """Test session management functionality."""

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self, api: LocaAPI) -> None:
        """Test creating a new session."""
        with patch("custom_components.loca.api.ClientSession") as mock_session_class:
            mock_session = AsyncMock(spec=ClientSession)
            mock_session_class.return_value = mock_session

            session = await api._get_session()

            assert session == mock_session
            assert api._session == mock_session
            mock_session_class.assert_called_once_with(
                timeout=ClientTimeout(total=30),
                headers={"Content-Type": "application/json"},
            )

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing(self, api: LocaAPI) -> None:
        """Test reusing existing session."""
        existing_session = AsyncMock(spec=ClientSession)
        api._session = existing_session

        session = await api._get_session()

        assert session == existing_session

    @pytest.mark.asyncio
    async def test_get_session_with_hass(self, api_with_session: LocaAPI) -> None:
        """Test getting session from Home Assistant."""
        # With hass set, it will try to get session from hass
        with patch(
            "custom_components.loca.api.aiohttp_client.async_get_clientsession"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            session = await api_with_session._get_session()
            assert session == mock_session
            mock_get_session.assert_called_once_with(api_with_session._hass)

    @pytest.mark.asyncio
    async def test_close_with_session(
        self, api: LocaAPI, mock_session: MagicMock
    ) -> None:
        """Test closing API with session (no hass)."""
        api._session = mock_session
        api._authenticated = True
        api._hass = None  # Ensure we're testing the standalone case

        with patch.object(api, "logout", new_callable=AsyncMock) as mock_logout:
            await api.close()

            mock_logout.assert_called_once()
            mock_session.close.assert_called_once()  # Session closed only when not managed by hass
            assert api._session is None
            assert api._authenticated is False

    @pytest.mark.asyncio
    async def test_close_without_session(self, api: LocaAPI) -> None:
        """Test closing API without session."""
        await api.close()
        assert api._session is None
        assert api._authenticated is False


class TestAuthentication:
    """Test authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_success(
        self, api: LocaAPI, mock_auth_response: dict
    ) -> None:
        """Test successful authentication."""
        mock_session = AsyncMock(spec=ClientSession)

        # Mock connectivity test
        mock_test_resp = MagicMock()
        mock_test_resp.status = 200

        # Mock auth response
        mock_auth_resp = MagicMock()
        mock_auth_resp.status = 200
        mock_auth_resp.json = AsyncMock(return_value=mock_auth_response)

        mock_session.get.return_value.__aenter__.return_value = mock_test_resp
        mock_session.post.return_value.__aenter__.return_value = mock_auth_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()

            assert result is True
            assert api._authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_no_user_object(self, api: LocaAPI) -> None:
        """Test authentication failure with no user object."""
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"error": "Invalid credentials"})

        mock_session.get.return_value.__aenter__.return_value = mock_resp
        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()

            assert result is False
            assert api._authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_http_error(self, api: LocaAPI) -> None:
        """Test authentication with HTTP error."""
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 401
        mock_resp.text = AsyncMock(return_value="Unauthorized")

        mock_session.get.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()

            assert result is False
            assert api._authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_exception(self, api: LocaAPI) -> None:
        """Test authentication with exception."""
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = aiohttp.ClientError("Network error")

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()

            assert result is False
            assert api._authenticated is False

    @pytest.mark.asyncio
    async def test_logout_success(self, api: LocaAPI) -> None:
        """Test successful logout."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"status": "ok"})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.logout()

            assert result is True
            assert api._authenticated is False

    @pytest.mark.asyncio
    async def test_logout_not_authenticated(self, api: LocaAPI) -> None:
        """Test logout when not authenticated."""
        api._authenticated = False

        result = await api.logout()

        assert result is True
        assert api._authenticated is False


class TestAssetManagement:
    """Test asset management functionality."""

    @pytest.mark.asyncio
    async def test_get_assets_success(
        self, api: LocaAPI, mock_assets_response: dict
    ) -> None:
        """Test successful asset retrieval."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_assets_response)

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()

            assert len(result) == 2
            assert result[0]["id"] == "12345"
            assert result[1]["id"] == "67890"

    @pytest.mark.asyncio
    async def test_get_assets_not_authenticated(self, api: LocaAPI) -> None:
        """Test asset retrieval when not authenticated."""
        api._authenticated = False

        with patch.object(api, "authenticate", return_value=False):
            result = await api.get_assets()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_assets_error_response(self, api: LocaAPI) -> None:
        """Test asset retrieval with error response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={"status": "error", "message": "Failed"}
        )

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_status_list_success(
        self, api: LocaAPI, mock_status_list_response: list
    ) -> None:
        """Test successful StatusList retrieval."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_status_list_response)

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_status_list()

            assert len(result) == 1
            assert result[0]["Asset"]["id"] == "12345"
            assert result[0]["Asset"]["label"] == "Test Device"


class TestDataParsing:
    """Test data parsing functionality."""

    def test_parse_status_as_device_complete(self, api: LocaAPI) -> None:
        """Test parsing complete status data."""
        status = {
            "Asset": {
                "id": "12345",
                "label": "Test Device",
                "type": 1,
                "brand": "BMW",
                "model": "X3",
            },
            "History": {
                "latitude": 52.3676,
                "longitude": 4.9041,
                "time": 1640995200,
                "charge": 85,
                "HDOP": 5,
                "SATU": 8,
                "speed": 65.5,
                "strength": 75,
            },
            "Spot": {
                "street": "Test Street",
                "number": "42",
                "city": "Amsterdam",
                "zipcode": "1234AB",
                "country": "Netherlands",
                "origin": 1,
            },
        }

        result = api.parse_status_as_device(status)

        assert result["device_id"] == "12345"
        assert result["name"] == "Test Device"
        assert result["latitude"] == 52.3676
        assert result["longitude"] == 4.9041
        assert result["battery_level"] == 85
        assert result["gps_accuracy"] == 5
        assert result["address"] == "Test Street 42, 1234AB Amsterdam, Netherlands"
        assert result["speed"] == 65.5
        assert result["satellites"] == 8
        assert result["asset_info"]["type"] == 1

    def test_parse_status_as_device_minimal(self, api: LocaAPI) -> None:
        """Test parsing minimal status data."""
        status = {
            "Asset": {"id": "67890"},
            "History": {"latitude": 51.5074, "longitude": -0.1278},
        }

        result = api.parse_status_as_device(status)

        assert result["device_id"] == "67890"
        assert result["name"] == "Loca Device 67890"
        assert result["latitude"] == 51.5074
        assert result["longitude"] == -0.1278
        assert result["battery_level"] is None
        assert result["gps_accuracy"] == 1  # Default HDOP value
        assert result["address"] is None

    def test_parse_location_as_device_complete(self, api: LocaAPI) -> None:
        """Test parsing complete location data."""
        location = {
            "id": "1",
            "label": "Home",
            "latitude": "51.876682",
            "longitude": "4.615142",
            "number": "30",
            "street": "Brouwerstraat",
            "city": "Ridderkerk",
            "state": "Zuid-Holland",
            "zipcode": "2984AR",
            "country": "Netherlands",
            "radius": "100",
            "update": "2022-04-26 19:35:06",
        }

        result = api.parse_location_as_device(location)

        assert result["device_id"] == "1"
        assert result["name"] == "Home"
        assert result["latitude"] == 51.876682
        assert result["longitude"] == 4.615142
        assert result["gps_accuracy"] == 100
        assert result["address"] == "Brouwerstraat 30, 2984AR Ridderkerk, Netherlands"
        assert isinstance(result["last_seen"], datetime)


class TestGroupManagement:
    """Test group management functionality."""

    @pytest.mark.asyncio
    async def test_get_groups_success(
        self, api: LocaAPI, mock_groups_response: dict
    ) -> None:
        """Test successful groups retrieval."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_groups_response)

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_groups()

            assert len(result) == 2
            assert result[0]["id"] == 248
            assert result[0]["label"] == "Autos"

    @pytest.mark.asyncio
    async def test_update_groups_cache(self, api: LocaAPI) -> None:
        """Test updating groups cache."""
        mock_groups = [
            {"id": 248, "label": "Autos"},
            {"id": 276, "label": "Motoren"},
            {"id": 300, "label": ""},
        ]

        with patch.object(api, "get_groups", return_value=mock_groups):
            await api.update_groups_cache()

            assert api._groups_cache[248] == "Autos"
            assert api._groups_cache[276] == "Motoren"
            assert api._groups_cache[300] == ""

    def test_get_group_name(self, api: LocaAPI) -> None:
        """Test getting group name from cache."""
        api._groups_cache = {248: "Autos", 276: "Motoren"}

        assert api.get_group_name(248) == "Autos"
        assert api.get_group_name(276) == "Motoren"
        assert api.get_group_name(999) == ""
        assert api.get_group_name(None) == ""


class TestLocationManagement:
    """Test location management functionality."""

    @pytest.mark.asyncio
    async def test_get_user_locations_success(
        self, api: LocaAPI, mock_locations_response: list
    ) -> None:
        """Test successful user locations retrieval."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_locations_response)

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_user_locations()

            assert len(result) == 1
            assert result[0]["id"] == "1"
            assert result[0]["label"] == "Home"

    @pytest.mark.asyncio
    async def test_get_user_locations_not_authenticated(self, api: LocaAPI) -> None:
        """Test user locations retrieval when not authenticated."""
        api._authenticated = False

        with patch.object(api, "authenticate", return_value=False):
            result = await api.get_user_locations()

            assert result == []


class TestErrorHandling:
    """Test error handling in API operations."""

    @pytest.mark.asyncio
    async def test_network_timeout(self, api: LocaAPI) -> None:
        """Test handling of network timeout."""
        from custom_components.loca.error_handling import LocaAPIUnavailableError

        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = TimeoutError()

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError):
                await api.get_assets()

    @pytest.mark.asyncio
    async def test_json_decode_error(self, api: LocaAPI) -> None:
        """Test handling of JSON decode errors."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()

            assert result == []

    @pytest.mark.asyncio
    async def test_server_error_response(self, api: LocaAPI) -> None:
        """Test handling of server error responses."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="Internal Server Error")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()

            assert result == []


class TestConcurrency:
    """Test concurrent API operations."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api: LocaAPI) -> None:
        """Test handling multiple concurrent requests."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"status": "ok", "assets": []})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            # Make multiple concurrent requests
            results = await asyncio.gather(
                api.get_assets(), api.get_assets(), api.get_assets()
            )

            assert all(isinstance(r, list) for r in results)
            assert len(results) == 3


class TestConnectivityErrors:
    """Test handling of connectivity errors that raise LocaAPIUnavailableError."""

    @pytest.mark.asyncio
    async def test_dns_error_raises_unavailable(self, api: LocaAPI) -> None:
        """Test that DNS errors raise LocaAPIUnavailableError."""
        from aiohttp import ClientConnectorDNSError

        from custom_components.loca.error_handling import LocaAPIUnavailableError

        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_key = MagicMock()
        mock_session.post.side_effect = ClientConnectorDNSError(
            mock_key, OSError("Timeout while contacting DNS servers")
        )

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError) as exc_info:
                await api.get_assets()

            assert "Cannot connect to Loca API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_refused_raises_unavailable(self, api: LocaAPI) -> None:
        """Test that connection refused errors raise LocaAPIUnavailableError."""
        from aiohttp import ClientConnectorError

        from custom_components.loca.error_handling import LocaAPIUnavailableError

        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_key = MagicMock()
        mock_session.post.side_effect = ClientConnectorError(
            mock_key, OSError("Connection refused")
        )

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError):
                await api.get_assets()

    @pytest.mark.asyncio
    async def test_timeout_error_raises_unavailable(self, api: LocaAPI) -> None:
        """Test that timeout errors raise LocaAPIUnavailableError."""
        from custom_components.loca.error_handling import LocaAPIUnavailableError

        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = TimeoutError("Request timed out")

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError) as exc_info:
                await api.get_assets()

            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_status_list_connectivity_error(self, api: LocaAPI) -> None:
        """Test connectivity error handling in get_status_list."""
        from custom_components.loca.error_handling import LocaAPIUnavailableError

        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = ConnectionError("Network unreachable")

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError):
                await api.get_status_list()

    @pytest.mark.asyncio
    async def test_groups_connectivity_error(self, api: LocaAPI) -> None:
        """Test connectivity error handling in get_groups."""
        from custom_components.loca.error_handling import LocaAPIUnavailableError

        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = OSError("No route to host")

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError):
                await api.get_groups()

    @pytest.mark.asyncio
    async def test_authentication_connectivity_error(self, api: LocaAPI) -> None:
        """Test connectivity error handling in authenticate."""
        from custom_components.loca.error_handling import LocaAPIUnavailableError

        mock_session = AsyncMock(spec=ClientSession)
        # Mock both GET (connectivity test) and POST (authentication) to fail
        mock_session.get.side_effect = TimeoutError("Connection timed out")
        mock_session.post.side_effect = TimeoutError("Connection timed out")

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(LocaAPIUnavailableError):
                await api.authenticate()


class TestHTTPStatusCodes:
    """Test handling of various HTTP status codes."""

    @pytest.mark.asyncio
    async def test_http_403_forbidden(self, api: LocaAPI) -> None:
        """Test handling of HTTP 403 Forbidden."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.text = AsyncMock(return_value="Forbidden")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            assert result == []

    @pytest.mark.asyncio
    async def test_http_404_not_found(self, api: LocaAPI) -> None:
        """Test handling of HTTP 404 Not Found."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.text = AsyncMock(return_value="Not Found")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            assert result == []

    @pytest.mark.asyncio
    async def test_http_429_rate_limit(self, api: LocaAPI) -> None:
        """Test handling of HTTP 429 Too Many Requests."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 429
        mock_resp.text = AsyncMock(return_value="Rate limit exceeded")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            assert result == []

    @pytest.mark.asyncio
    async def test_http_503_service_unavailable(self, api: LocaAPI) -> None:
        """Test handling of HTTP 503 Service Unavailable."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 503
        mock_resp.text = AsyncMock(return_value="Service Unavailable")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            assert result == []


class TestAPIProperties:
    """Test API public properties."""

    def test_is_authenticated_property(self, api: LocaAPI) -> None:
        """Test is_authenticated property."""
        assert api.is_authenticated is False
        api._authenticated = True
        assert api.is_authenticated is True

    def test_has_credentials_property(self, api: LocaAPI) -> None:
        """Test has_credentials property."""
        assert api.has_credentials is True  # All credentials set in fixture

        # Test with missing api_key
        api_no_key = LocaAPI("", "user", "pass")
        assert api_no_key.has_credentials is False

        # Test with missing username
        api_no_user = LocaAPI("key", "", "pass")
        assert api_no_user.has_credentials is False

    def test_groups_cache_size_property(self, api: LocaAPI) -> None:
        """Test groups_cache_size property."""
        assert api.groups_cache_size == 0

        api._groups_cache = {1: "Group 1", 2: "Group 2", 3: "Group 3"}
        assert api.groups_cache_size == 3


class TestParseJsonOrLog:
    """Test _parse_json_or_log method."""

    @pytest.mark.asyncio
    async def test_successful_parse(self, api: LocaAPI) -> None:
        """Test successful JSON parsing."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={"key": "value"})

        result = await api._parse_json_or_log(mock_response, "Test op")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_parse_failure_returns_none(self, api: LocaAPI) -> None:
        """Test that parse failure returns None."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        result = await api._parse_json_or_log(mock_response, "Test op")
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_failure_with_context(
        self, api: LocaAPI, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that parse failure logs with context."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(side_effect=ValueError("bad json"))

        import logging

        with caplog.at_level(logging.ERROR):
            result = await api._parse_json_or_log(
                mock_response, "Test op", context="after reauth"
            )

        assert result is None
        assert "after reauth" in caplog.text


class TestReauthAndRetry:
    """Test _reauth_and_retry method."""

    @pytest.mark.asyncio
    async def test_reauth_success_and_retry(self, api: LocaAPI) -> None:
        """Test successful reauthentication and retry."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        # Retry response succeeds
        mock_retry_resp = MagicMock()
        mock_retry_resp.status = 200
        mock_retry_resp.json = AsyncMock(return_value={"data": "ok"})
        mock_session.post.return_value.__aenter__.return_value = mock_retry_resp

        with patch.object(api, "authenticate", return_value=True):
            result = await api._reauth_and_retry(
                mock_session,
                "https://api.loca.nl/v1/StatusList.json",
                {"key": "test"},
                "Test op",
            )
        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_reauth_failure(self, api: LocaAPI) -> None:
        """Test reauthentication failure returns None."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        with patch.object(api, "authenticate", return_value=False):
            result = await api._reauth_and_retry(
                mock_session,
                "https://api.loca.nl/v1/StatusList.json",
                {"key": "test"},
                "Test op",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_reauth_success_retry_fails(self, api: LocaAPI) -> None:
        """Test reauth succeeds but retry request fails."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_retry_resp = MagicMock()
        mock_retry_resp.status = 500
        mock_session.post.return_value.__aenter__.return_value = mock_retry_resp

        with patch.object(api, "authenticate", return_value=True):
            result = await api._reauth_and_retry(
                mock_session,
                "https://api.loca.nl/v1/StatusList.json",
                {"key": "test"},
                "Test op",
            )
        assert result is None


class TestExtractAssets:
    """Test _extract_assets method."""

    def test_list_response(self, api: LocaAPI) -> None:
        """Test extracting assets from a list response."""
        data = [{"id": "1"}, {"id": "2"}]
        result = api._extract_assets(data)
        assert result == data

    def test_dict_with_assets_key(self, api: LocaAPI) -> None:
        """Test extracting assets from dict with 'assets' key."""
        data = {"assets": [{"id": "1"}]}
        result = api._extract_assets(data)
        assert result == [{"id": "1"}]

    def test_dict_keyed_by_id(self, api: LocaAPI) -> None:
        """Test fallback parsing for dict keyed by numeric strings."""
        data = {"123": {"id": "123", "name": "Device"}}
        result = api._extract_assets(data)
        assert result == [{"id": "123", "name": "Device"}]

    def test_dict_keyed_by_asset_prefix(self, api: LocaAPI) -> None:
        """Test fallback parsing for dict keyed by 'asset' prefix."""
        data = {"asset_1": {"id": "1"}}
        result = api._extract_assets(data)
        assert result == [{"id": "1"}]

    def test_dict_keyed_by_id_non_dict_values(self, api: LocaAPI) -> None:
        """Test fallback parsing when values are not dicts."""
        data = {"123": "not_a_dict"}
        result = api._extract_assets(data)
        assert result == []

    def test_unrecognized_dict(self, api: LocaAPI) -> None:
        """Test that unrecognized dict returns None."""
        data = {"status": "error", "message": "Bad request"}
        result = api._extract_assets(data)
        assert result is None

    def test_non_dict_non_list(self, api: LocaAPI) -> None:
        """Test non-dict, non-list returns None."""
        result = api._extract_assets("string")
        assert result is None

    def test_none_input(self, api: LocaAPI) -> None:
        """Test None input returns None."""
        result = api._extract_assets(None)
        assert result is None


class TestExtractListFromResponse:
    """Test _extract_list_from_response static method."""

    def test_direct_list(self) -> None:
        """Test extraction from direct list."""
        data = [{"id": 1}, {"id": 2}]
        result, source = LocaAPI._extract_list_from_response(data, ["items"])
        assert result == data
        assert source == "direct array"

    def test_dict_with_matching_key(self) -> None:
        """Test extraction from dict with matching key."""
        data = {"StatusList": [{"id": 1}], "other": "value"}
        result, source = LocaAPI._extract_list_from_response(
            data, ["StatusList", "devices"]
        )
        assert result == [{"id": 1}]
        assert source == "StatusList"

    def test_nested_dict_extraction(self) -> None:
        """Test extraction from nested dict using tuple candidate."""
        data = {"response": {"UserLocationList": [{"id": 1}]}}
        result, source = LocaAPI._extract_list_from_response(
            data, [("response", "UserLocationList")]
        )
        assert result == [{"id": 1}]
        assert source == "response.UserLocationList"

    def test_no_match(self) -> None:
        """Test no match returns None."""
        data = {"unknown_key": "value"}
        result, source = LocaAPI._extract_list_from_response(
            data, ["StatusList", "devices"]
        )
        assert result is None
        assert source == ""

    def test_non_dict_non_list(self) -> None:
        """Test non-dict, non-list returns None."""
        result, source = LocaAPI._extract_list_from_response("string", ["items"])
        assert result is None
        assert source == ""

    def test_nested_parent_not_dict(self) -> None:
        """Test nested extraction when parent is not a dict."""
        data = {"response": "not_a_dict"}
        result, _source = LocaAPI._extract_list_from_response(
            data, [("response", "items")]
        )
        assert result is None

    def test_nested_child_not_list(self) -> None:
        """Test nested extraction when child is not a list."""
        data = {"response": {"items": "not_a_list"}}
        result, _source = LocaAPI._extract_list_from_response(
            data, [("response", "items")]
        )
        assert result is None

    def test_candidate_value_not_list(self) -> None:
        """Test that non-list candidate values are skipped."""
        data = {"StatusList": "not a list", "devices": [{"id": 1}]}
        result, source = LocaAPI._extract_list_from_response(
            data, ["StatusList", "devices"]
        )
        assert result == [{"id": 1}]
        assert source == "devices"


class TestLogUnexpectedResponse:
    """Test _log_unexpected_response method."""

    def test_dict_with_error_message(
        self, api: LocaAPI, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging dict response with error message."""
        import logging

        with caplog.at_level(logging.ERROR):
            api._log_unexpected_response("Test", {"message": "Auth failed"})
        assert "Auth failed" in caplog.text

    def test_dict_without_error_message(
        self, api: LocaAPI, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging dict response without error message."""
        import logging

        with caplog.at_level(logging.ERROR):
            api._log_unexpected_response("Test", {"unknown_key": "value"})
        assert "Unexpected response format" in caplog.text

    def test_non_dict_response(
        self, api: LocaAPI, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging non-dict response."""
        import logging

        with caplog.at_level(logging.ERROR):
            api._log_unexpected_response("Test", "string_response")
        assert "Unexpected Test response type" in caplog.text


class TestPostAndRetryOn401:
    """Test _post_and_retry_on_401 method."""

    @pytest.mark.asyncio
    async def test_401_triggers_reauth_and_retry(self, api: LocaAPI) -> None:
        """Test that 401 triggers reauthentication and retry."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        # First response: 401
        mock_resp_401 = MagicMock()
        mock_resp_401.status = 401

        mock_session.post.return_value.__aenter__.return_value = mock_resp_401

        with (
            patch.object(api, "_get_session", return_value=mock_session),
            patch.object(
                api,
                "_reauth_and_retry",
                return_value={"status": "ok"},
            ) as mock_reauth,
        ):
            result = await api._post_and_retry_on_401("TestEndpoint.json", "Test op")

        assert result == {"status": "ok"}
        mock_reauth.assert_called_once()

    @pytest.mark.asyncio
    async def test_403_triggers_reauth_and_retry(self, api: LocaAPI) -> None:
        """Test that 403 triggers reauthentication and retry."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp_403 = MagicMock()
        mock_resp_403.status = 403

        mock_session.post.return_value.__aenter__.return_value = mock_resp_403

        with (
            patch.object(api, "_get_session", return_value=mock_session),
            patch.object(
                api,
                "_reauth_and_retry",
                return_value=None,
            ) as mock_reauth,
        ):
            result = await api._post_and_retry_on_401("TestEndpoint.json", "Test op")

        assert result is None
        mock_reauth.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_auth_error_returns_none(self, api: LocaAPI) -> None:
        """Test that generic exceptions return None (not connectivity)."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = ValueError("Unexpected error")

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api._post_and_retry_on_401("TestEndpoint.json", "Test op")

        assert result is None

    @pytest.mark.asyncio
    async def test_not_authenticated_calls_authenticate(self, api: LocaAPI) -> None:
        """Test that unauthenticated client calls authenticate first."""
        api._authenticated = False

        with patch.object(api, "authenticate", return_value=False) as mock_auth:
            result = await api._post_and_retry_on_401("TestEndpoint.json", "Test op")

        assert result is None
        mock_auth.assert_called_once()


class TestAPIResponseHelperAdditional:
    """Test additional APIResponseHelper methods."""

    def test_extract_error_message_various_fields(self) -> None:
        """Test error message extraction from various field names."""
        from custom_components.loca.api import APIResponseHelper

        assert APIResponseHelper.extract_error_message({"message": "err1"}) == "err1"
        assert APIResponseHelper.extract_error_message({"error": "err2"}) == "err2"
        assert (
            APIResponseHelper.extract_error_message({"description": "err3"}) == "err3"
        )
        assert APIResponseHelper.extract_error_message({"detail": "err4"}) == "err4"
        assert APIResponseHelper.extract_error_message({"reason": "err5"}) == "err5"
        assert APIResponseHelper.extract_error_message({}) is None

    def test_format_dutch_address_full(self) -> None:
        """Test formatting Dutch address with all parts."""
        from custom_components.loca.api import APIResponseHelper

        data = {
            "street": "Brouwerstraat",
            "number": "30",
            "zipcode": "2984AR",
            "city": "Ridderkerk",
            "country": "Netherlands",
        }
        result = APIResponseHelper.format_dutch_address(data)
        assert result == "Brouwerstraat 30, 2984AR Ridderkerk, Netherlands"

    def test_format_dutch_address_street_only(self) -> None:
        """Test formatting Dutch address with street only."""
        from custom_components.loca.api import APIResponseHelper

        data = {"street": "Brouwerstraat"}
        result = APIResponseHelper.format_dutch_address(data)
        assert result == "Brouwerstraat"

    def test_format_dutch_address_empty(self) -> None:
        """Test formatting Dutch address with empty data."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.format_dutch_address({})
        assert result is None

    def test_format_dutch_address_city_only(self) -> None:
        """Test formatting Dutch address with city only."""
        from custom_components.loca.api import APIResponseHelper

        data = {"city": "Amsterdam"}
        result = APIResponseHelper.format_dutch_address(data)
        assert result == "Amsterdam"

    def test_safe_int_conversion(self) -> None:
        """Test safe integer conversion."""
        from custom_components.loca.api import APIResponseHelper

        assert APIResponseHelper.safe_int_conversion(42) == 42
        assert APIResponseHelper.safe_int_conversion("42") == 42
        assert APIResponseHelper.safe_int_conversion(42.7) == 42
        assert APIResponseHelper.safe_int_conversion(None) == 0
        assert APIResponseHelper.safe_int_conversion("invalid") == 0
        assert APIResponseHelper.safe_int_conversion(None, default=5) == 5

    def test_safe_float_conversion(self) -> None:
        """Test safe float conversion."""
        from custom_components.loca.api import APIResponseHelper

        assert APIResponseHelper.safe_float_conversion(3.14) == 3.14
        assert APIResponseHelper.safe_float_conversion("3.14") == 3.14
        assert APIResponseHelper.safe_float_conversion(42) == 42.0
        assert APIResponseHelper.safe_float_conversion(None) == 0.0
        assert APIResponseHelper.safe_float_conversion("invalid") == 0.0
        assert APIResponseHelper.safe_float_conversion(None, default=1.5) == 1.5


class TestAuthenticationEdgeCases:
    """Test authentication edge cases."""

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self) -> None:
        """Test authentication with missing credentials."""
        api = LocaAPI("", "", "")
        result = await api.authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_json_parse_error(self, api: LocaAPI) -> None:
        """Test authentication with JSON parse error in 200 response."""
        mock_session = AsyncMock(spec=ClientSession)

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200

        mock_auth_resp = MagicMock()
        mock_auth_resp.status = 200
        mock_auth_resp.json = AsyncMock(side_effect=ValueError("Bad JSON"))
        mock_auth_resp.text = AsyncMock(return_value="<html>Not JSON</html>")

        mock_session.get.return_value.__aenter__.return_value = mock_test_resp
        mock_session.post.return_value.__aenter__.return_value = mock_auth_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_no_user_but_no_error(self, api: LocaAPI) -> None:
        """Test authentication response with no user and no error field."""
        mock_session = AsyncMock(spec=ClientSession)

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200

        mock_auth_resp = MagicMock()
        mock_auth_resp.status = 200
        mock_auth_resp.json = AsyncMock(return_value={"status": "ok"})

        mock_session.get.return_value.__aenter__.return_value = mock_test_resp
        mock_session.post.return_value.__aenter__.return_value = mock_auth_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_http_error_text_read_failure(
        self, api: LocaAPI
    ) -> None:
        """Test authentication with HTTP error where text() fails."""
        mock_session = AsyncMock(spec=ClientSession)

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200

        mock_auth_resp = MagicMock()
        mock_auth_resp.status = 500
        mock_auth_resp.text = AsyncMock(side_effect=Exception("read failed"))

        mock_session.get.return_value.__aenter__.return_value = mock_test_resp
        mock_session.post.return_value.__aenter__.return_value = mock_auth_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_auth_error_ssl(self, api: LocaAPI) -> None:
        """Test _handle_auth_error with SSL error."""
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = Exception("SSL certificate verify failed")

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_test_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_auth_error_403(self, api: LocaAPI) -> None:
        """Test _handle_auth_error with 403 forbidden."""
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = Exception("403 Forbidden access")

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_test_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_auth_error_404(self, api: LocaAPI) -> None:
        """Test _handle_auth_error with 404 not found."""
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = Exception("404 Not Found")

        mock_test_resp = MagicMock()
        mock_test_resp.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_test_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.authenticate()
            assert result is False


class TestLogoutEdgeCases:
    """Test logout edge cases."""

    @pytest.mark.asyncio
    async def test_logout_error_response(self, api: LocaAPI) -> None:
        """Test logout with error in response data."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={"status": "error", "message": "Session expired"}
        )

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.logout()
            assert result is False

    @pytest.mark.asyncio
    async def test_logout_http_error(self, api: LocaAPI) -> None:
        """Test logout with HTTP error."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 500

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.logout()
            assert result is False

    @pytest.mark.asyncio
    async def test_logout_connectivity_error(self, api: LocaAPI) -> None:
        """Test logout with connectivity error."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = ConnectionError("Network down")

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.logout()
            assert result is False

    @pytest.mark.asyncio
    async def test_logout_non_connectivity_error(self, api: LocaAPI) -> None:
        """Test logout with non-connectivity error."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = ValueError("Unexpected")

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.logout()
            assert result is False


class TestGetAssetsEdgeCases:
    """Test get_assets with edge cases."""

    @pytest.mark.asyncio
    async def test_get_assets_empty_list(self, api: LocaAPI) -> None:
        """Test get_assets returns empty list for empty assets."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"assets": []})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            assert result == []


class TestGetStatusListEdgeCases:
    """Test get_status_list edge cases."""

    @pytest.mark.asyncio
    async def test_get_status_list_dict_response(self, api: LocaAPI) -> None:
        """Test get_status_list with dict containing StatusList key."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={"StatusList": [{"Asset": {"id": "1"}}]}
        )

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_status_list()
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_status_list_unexpected_response(self, api: LocaAPI) -> None:
        """Test get_status_list with unexpected response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"status": "error"})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_status_list()
            assert result == []


class TestGetUserLocationsEdgeCases:
    """Test get_user_locations edge cases."""

    @pytest.mark.asyncio
    async def test_get_user_locations_nested_response(self, api: LocaAPI) -> None:
        """Test get_user_locations with nested response format."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={
                "response": {"UserLocationList": [{"id": "1", "label": "Home"}]}
            }
        )

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_user_locations()
            assert len(result) == 1
            assert result[0]["label"] == "Home"

    @pytest.mark.asyncio
    async def test_get_user_locations_unexpected_response(self, api: LocaAPI) -> None:
        """Test get_user_locations with unexpected response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"error": "not found"})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_user_locations()
            assert result == []


class TestGetGroupsEdgeCases:
    """Test get_groups edge cases."""

    @pytest.mark.asyncio
    async def test_get_groups_direct_array(self, api: LocaAPI) -> None:
        """Test get_groups with direct array response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[{"id": 1, "label": "Group 1"}])

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_groups()
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_groups_error_response_dict(self, api: LocaAPI) -> None:
        """Test get_groups with error dict response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"error": "Unauthorized"})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_groups()
            assert result == []

    @pytest.mark.asyncio
    async def test_get_groups_unexpected_format(self, api: LocaAPI) -> None:
        """Test get_groups with unexpected format dict."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"status": "ok"})

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_groups()
            assert result == []

    @pytest.mark.asyncio
    async def test_get_groups_non_dict_non_list(self, api: LocaAPI) -> None:
        """Test get_groups with non-dict, non-list response."""
        api._authenticated = True
        mock_session = AsyncMock(spec=ClientSession)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value="not a valid response")

        mock_session.post.return_value.__aenter__.return_value = mock_resp

        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_groups()
            assert result == []

    @pytest.mark.asyncio
    async def test_get_groups_not_authenticated(self, api: LocaAPI) -> None:
        """Test get_groups when not authenticated."""
        api._authenticated = False

        with patch.object(api, "authenticate", return_value=False):
            result = await api.get_groups()
            assert result == []


class TestTimestampParsing:
    """Test timestamp parsing in APIResponseHelper."""

    def test_parse_unix_timestamp(self) -> None:
        """Test parsing Unix timestamp (integer)."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp(1640995200)
        assert result is not None
        assert result.year == 2022
        assert result.month == 1
        assert result.day == 1

    def test_parse_unix_timestamp_float(self) -> None:
        """Test parsing Unix timestamp (float)."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp(1640995200.5)
        assert result is not None
        assert result.year == 2022

    def test_parse_iso_timestamp_with_z(self) -> None:
        """Test parsing ISO timestamp with Z timezone."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("2022-01-01T12:00:00Z")
        assert result is not None
        assert result.year == 2022
        assert result.hour == 12

    def test_parse_iso_timestamp_with_offset(self) -> None:
        """Test parsing ISO timestamp with timezone offset."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("2022-01-01T12:00:00+01:00")
        assert result is not None
        assert result.year == 2022

    def test_parse_iso_timestamp_no_timezone(self) -> None:
        """Test parsing ISO timestamp without timezone."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("2022-01-01T12:00:00")
        assert result is not None
        assert result.year == 2022

    def test_parse_unix_timestamp_string(self) -> None:
        """Test parsing Unix timestamp as string."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("1640995200")
        assert result is not None
        assert result.year == 2022

    def test_parse_timestamp_none(self) -> None:
        """Test parsing None timestamp."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp(None)
        assert result is None

    def test_parse_timestamp_empty_string(self) -> None:
        """Test parsing empty string timestamp."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("")
        assert result is None

    def test_parse_timestamp_invalid(self) -> None:
        """Test parsing invalid timestamp."""
        from custom_components.loca.api import APIResponseHelper

        result = APIResponseHelper.parse_timestamp("not-a-timestamp")
        assert result is None
