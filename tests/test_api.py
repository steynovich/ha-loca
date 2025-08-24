"""Tests for Loca API client."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import aiohttp
import pytest
from aiohttp import ClientSession, ClientTimeout

from custom_components.loca.api import LocaAPI
from custom_components.loca.const import API_BASE_URL


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
            "email": "test@example.com"
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
                "serial": "ABC123"
            },
            "History": {
                "latitude": 52.3676,
                "longitude": 4.9041,
                "time": 1640995200,
                "charge": 85,
                "HDOP": 5,
                "SATU": 8,
                "speed": 65.5,
                "strength": 75
            },
            "Spot": {
                "street": "Test Street",
                "number": "42",
                "city": "Amsterdam",
                "zipcode": "1234AB",
                "country": "Netherlands",
                "origin": 1
            }
        }
    ]


@pytest.fixture
def mock_groups_response() -> dict[str, Any]:
    """Mock successful groups response."""
    return {
        "groups": [
            {"id": 248, "label": "Autos", "account": 2},
            {"id": 276, "label": "Motoren", "account": 2}
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
            "radius": "100"
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
        with patch("custom_components.loca.api.aiohttp_client.async_get_clientsession") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            session = await api_with_session._get_session()
            assert session == mock_session
            mock_get_session.assert_called_once_with(api_with_session._hass)
    
    @pytest.mark.asyncio
    async def test_close_with_session(self, api: LocaAPI, mock_session: MagicMock) -> None:
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
    async def test_authenticate_success(self, api: LocaAPI, mock_auth_response: dict) -> None:
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
    async def test_get_assets_success(self, api: LocaAPI, mock_assets_response: dict) -> None:
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
        mock_resp.json = AsyncMock(return_value={"status": "error", "message": "Failed"})
        
        mock_session.post.return_value.__aenter__.return_value = mock_resp
        
        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_status_list_success(self, api: LocaAPI, mock_status_list_response: list) -> None:
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
                "model": "X3"
            },
            "History": {
                "latitude": 52.3676,
                "longitude": 4.9041,
                "time": 1640995200,
                "charge": 85,
                "HDOP": 5,
                "SATU": 8,
                "speed": 65.5,
                "strength": 75
            },
            "Spot": {
                "street": "Test Street",
                "number": "42",
                "city": "Amsterdam",
                "zipcode": "1234AB",
                "country": "Netherlands",
                "origin": 1
            }
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
            "Asset": {
                "id": "67890"
            },
            "History": {
                "latitude": 51.5074,
                "longitude": -0.1278
            }
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
            "update": "2022-04-26 19:35:06"
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
    async def test_get_groups_success(self, api: LocaAPI, mock_groups_response: dict) -> None:
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
            {"id": 300, "label": ""}
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
    async def test_get_user_locations_success(self, api: LocaAPI, mock_locations_response: list) -> None:
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
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.post.side_effect = asyncio.TimeoutError()
        
        with patch.object(api, "_get_session", return_value=mock_session):
            result = await api.get_assets()
            
            assert result == []
    
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
                api.get_assets(),
                api.get_assets(),
                api.get_assets()
            )
            
            assert all(isinstance(r, list) for r in results)
            assert len(results) == 3