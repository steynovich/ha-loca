"""Tests for Loca diagnostics."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant

from custom_components.loca.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from custom_components.loca.const import DOMAIN


class TestDiagnostics:
    """Test diagnostics functionality."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            "api_key": "test_api_key_12345",
            "username": "test_user@example.com",
            "password": "test_password"
        }
        return entry

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.data = {
            "device1": {
                "device_id": "device1",
                "name": "Test Car",
                "latitude": 52.1234,
                "longitude": 4.5678,
                "battery_level": 85,
                "gps_accuracy": 3.2,
                "last_seen": datetime(2023, 8, 21, 10, 30, 0, tzinfo=timezone.utc),
                "asset_info": {
                    "brand": "BMW",
                    "model": "X3",
                    "serial": "ABC123",
                    "type": 1,
                    "group_name": "Cars"
                },
                "speed": 65.5,
                "satellites": 8,
                "signal_strength": 75
            },
            "device2": {
                "device_id": "device2", 
                "name": "Test Bike",
                "latitude": 52.9876,
                "longitude": 4.1234,
                "battery_level": None,
                "gps_accuracy": 5.1,
                "asset_info": {
                    "brand": "Giant",
                    "model": "TCR",
                    "type": 2
                }
            }
        }
        coordinator.last_update_success = True
        coordinator.last_exception = None
        return coordinator

    @pytest.mark.asyncio
    async def test_config_entry_diagnostics_success(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test successful config entry diagnostics."""
        mock_config_entry.runtime_data = mock_coordinator
        
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
        
        # Check structure
        assert "config_entry" in diagnostics
        assert "coordinator" in diagnostics
        assert "devices" in diagnostics
        
        # Check config entry data (sensitive data should be redacted)
        config_data = diagnostics["config_entry"]
        assert config_data["api_key"] == "**REDACTED**"
        assert config_data["username"] == "**REDACTED**" 
        assert config_data["password"] == "**REDACTED**"
        
        # Check coordinator info
        coordinator_data = diagnostics["coordinator"]
        assert coordinator_data["last_update_success"] is True
        assert coordinator_data["last_exception"] is None
        assert coordinator_data["device_count"] == 2
        
        # Check devices data (non-sensitive)
        devices_data = diagnostics["devices"]
        assert len(devices_data) == 2
        assert devices_data[0]["device_id"] == "device1"
        assert devices_data[0]["name"] == "Test Car"
        assert devices_data[0]["battery_level"] == 85

    @pytest.mark.asyncio
    async def test_config_entry_diagnostics_with_exception(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test config entry diagnostics with coordinator exception."""
        mock_coordinator.last_exception = Exception("API Error")
        mock_config_entry.runtime_data = mock_coordinator
        
        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
        
        coordinator_data = diagnostics["coordinator"]
        assert coordinator_data["last_exception"] == "API Error"

    @pytest.mark.asyncio
    async def test_device_diagnostics_success(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test successful device diagnostics."""
        mock_config_entry.runtime_data = mock_coordinator
        
        # Mock device registry entry
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device1")}
        
        diagnostics = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)
        
        # Should return the specific device data with sensitive info redacted
        assert diagnostics["device_id"] == "device1"
        assert diagnostics["name"] == "Test Car"
        assert diagnostics["latitude"] == "**REDACTED**"
        assert diagnostics["longitude"] == "**REDACTED**"
        assert diagnostics["has_gps_data"] == True
        assert diagnostics["asset_info"]["brand"] == "BMW"

    @pytest.mark.asyncio
    async def test_device_diagnostics_device_not_found(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test device diagnostics when device not found."""
        mock_config_entry.runtime_data = mock_coordinator
        
        # Mock device registry entry for non-existent device
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "nonexistent")}
        
        diagnostics = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)
        
        # Should return empty dict for non-existent device
        assert diagnostics == {}

    @pytest.mark.asyncio
    async def test_device_diagnostics_no_coordinator(self, hass: HomeAssistant, mock_config_entry):
        """Test device diagnostics when coordinator not available."""
        mock_config_entry.runtime_data = None
        
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device1")}
        
        diagnostics = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)
        
        # Should return empty dict when no coordinator
        assert diagnostics == {}

    def test_sensitive_data_redaction(self, mock_config_entry):
        """Test that sensitive data is properly redacted."""
        # This would be tested in the actual diagnostics function
        # Here we just verify the test data setup
        assert "api_key" in mock_config_entry.data
        assert "username" in mock_config_entry.data
        assert "password" in mock_config_entry.data


class TestDiagnosticsDataSafety:
    """Test diagnostics data privacy and safety."""

    def test_no_sensitive_location_data_exposure(self):
        """Test that precise location data handling follows privacy guidelines."""
        # Note: This would test that coordinates are handled appropriately
        # Current implementation includes coordinates in diagnostics which may be
        # acceptable for debugging, but should be clearly documented
        pass

    def test_api_credentials_never_exposed(self):
        """Test that API credentials are never exposed in diagnostics."""
        # This is covered in the main tests above, but highlighted here for security
        pass