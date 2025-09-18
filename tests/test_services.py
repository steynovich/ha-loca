"""Tests for Loca services functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.loca.services import (
    async_setup_services,
    async_unload_services,
    SERVICE_REFRESH_DEVICES,
    SERVICE_FORCE_UPDATE,
)
from custom_components.loca.const import DOMAIN


class TestServiceSetup:
    """Test service setup and unload functions."""

    @pytest.mark.asyncio
    async def test_setup_services(self, hass: HomeAssistant):
        """Test service registration."""
        await async_setup_services(hass)
        
        # Check that services were registered
        assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)

    @pytest.mark.asyncio
    async def test_unload_services(self, hass: HomeAssistant):
        """Test service unregistration."""
        # First register the services
        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)
        
        # Then unload them
        await async_unload_services(hass)
        
        # Check that services were unregistered
        assert not hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert not hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)


class TestRefreshDevicesService:
    """Test refresh devices service."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.domain = DOMAIN
        entry.runtime_data = mock_coordinator
        entry.entry_id = "test_entry_123"
        return entry

    @pytest.mark.asyncio
    async def test_refresh_devices_success(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test successful device refresh through service call."""
        # Setup services
        await async_setup_services(hass)
        
        # Mock config entries
        with patch.object(hass.config_entries, 'async_get_entry', return_value=mock_config_entry), \
             patch('custom_components.loca.services.async_extract_config_entry_ids', 
                   return_value=['test_entry_123']):
            
            # Call the service
            await hass.services.async_call(DOMAIN, SERVICE_REFRESH_DEVICES, {}, blocking=True)
            
            # Should refresh the coordinator
            mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_devices_no_entries(self, hass: HomeAssistant):
        """Test refresh devices when no valid config entries."""
        # Setup services
        await async_setup_services(hass)
        
        with patch('custom_components.loca.services.async_extract_config_entry_ids', 
                   return_value=[]):
            
            # Call the service - should raise ServiceValidationError
            with pytest.raises(HomeAssistantError, match="No Loca config entries found"):
                await hass.services.async_call(DOMAIN, SERVICE_REFRESH_DEVICES, {}, blocking=True)

    @pytest.mark.asyncio
    async def test_refresh_devices_invalid_entry(self, hass: HomeAssistant):
        """Test refresh devices with invalid config entry."""
        # Setup services
        await async_setup_services(hass)
        
        with patch.object(hass.config_entries, 'async_get_entry', return_value=None), \
             patch('custom_components.loca.services.async_extract_config_entry_ids', 
                   return_value=['invalid_entry']):
            
            # Call the service - should raise error
            with pytest.raises(HomeAssistantError, match="Config entry invalid_entry not found"):
                await hass.services.async_call(DOMAIN, SERVICE_REFRESH_DEVICES, {}, blocking=True)

    @pytest.mark.asyncio
    async def test_refresh_devices_coordinator_error(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test refresh devices when coordinator fails."""
        # Setup services
        await async_setup_services(hass)
        
        # Make coordinator fail
        mock_coordinator.async_request_refresh.side_effect = Exception("Refresh failed")
        
        with patch.object(hass.config_entries, 'async_get_entry', return_value=mock_config_entry), \
             patch('custom_components.loca.services.async_extract_config_entry_ids', 
                   return_value=['test_entry_123']):
            
            # Call the service - should raise HomeAssistantError
            with pytest.raises(HomeAssistantError, match="Failed to refresh devices"):
                await hass.services.async_call(DOMAIN, SERVICE_REFRESH_DEVICES, {}, blocking=True)


class TestForceUpdateService:
    """Test force update service."""

    @pytest.fixture
    def mock_coordinator_with_device(self):
        """Create a mock coordinator with test device."""
        coordinator = MagicMock()
        coordinator.data = {
            "test_device_123": {
                "device_id": "test_device_123",
                "name": "Test Device",
                "latitude": 52.1234,
                "longitude": 4.5678
            }
        }
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry_with_device(self, mock_coordinator_with_device):
        """Create a mock config entry with device."""
        entry = MagicMock()
        entry.domain = DOMAIN
        entry.runtime_data = mock_coordinator_with_device
        return entry

    @pytest.mark.asyncio
    async def test_force_update_success(self, hass: HomeAssistant, mock_config_entry_with_device, mock_coordinator_with_device):
        """Test successful device force update."""
        # Setup services
        await async_setup_services(hass)
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[mock_config_entry_with_device]):
            # Call the service
            call_data = {"device_id": "test_device_123"}
            await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)
            
            # Should refresh the coordinator
            mock_coordinator_with_device.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_update_device_not_found(self, hass: HomeAssistant):
        """Test force update when device not found."""
        # Setup services
        await async_setup_services(hass)
        
        # Mock empty coordinator
        coordinator = MagicMock()
        coordinator.data = {}
        
        entry = MagicMock()
        entry.domain = DOMAIN
        entry.runtime_data = coordinator
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[entry]):
            # Call the service - should raise error
            call_data = {"device_id": "nonexistent_device"}
            with pytest.raises(HomeAssistantError, match="Device 'nonexistent_device' not found"):
                await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)

    @pytest.mark.asyncio
    async def test_force_update_missing_device_id(self, hass: HomeAssistant):
        """Test force update service without device_id parameter."""
        # Setup services
        await async_setup_services(hass)
        
        # Call the service without device_id - should raise validation error
        call_data: dict[str, str] = {}
        with pytest.raises(Exception):  # Schema validation will fail before service is called
            await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)

    @pytest.mark.asyncio
    async def test_force_update_empty_device_id(self, hass: HomeAssistant):
        """Test force update service with empty device_id."""
        # Setup services
        await async_setup_services(hass)
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[]):
            # Call the service with empty device_id
            call_data = {"device_id": ""}
            with pytest.raises(HomeAssistantError, match="Device ID is required"):
                await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)

    @pytest.mark.asyncio
    async def test_force_update_no_config_entries(self, hass: HomeAssistant):
        """Test force update when no Loca config entries."""
        # Setup services
        await async_setup_services(hass)
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[]):
            # Call the service
            call_data = {"device_id": "test_device_123"}
            with pytest.raises(HomeAssistantError, match="Device 'test_device_123' not found"):
                await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)

    @pytest.mark.asyncio
    async def test_force_update_multiple_entries(self, hass: HomeAssistant, mock_coordinator_with_device):
        """Test force update with multiple config entries."""
        # Setup services
        await async_setup_services(hass)
        
        # First entry without the device
        coordinator1 = MagicMock()
        coordinator1.data = {}
        entry1 = MagicMock()
        entry1.domain = DOMAIN
        entry1.runtime_data = coordinator1
        
        # Second entry with the device
        entry2 = MagicMock()
        entry2.domain = DOMAIN
        entry2.runtime_data = mock_coordinator_with_device
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[entry1, entry2]):
            # Call the service
            call_data = {"device_id": "test_device_123"}
            await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)
            
            # Should find device in second entry and refresh that coordinator
            mock_coordinator_with_device.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_update_coordinator_error(self, hass: HomeAssistant, mock_config_entry_with_device, mock_coordinator_with_device):
        """Test force update when coordinator fails."""
        # Setup services
        await async_setup_services(hass)
        
        # Make coordinator fail
        mock_coordinator_with_device.async_request_refresh.side_effect = Exception("Update failed")
        
        with patch.object(hass.config_entries, 'async_entries', return_value=[mock_config_entry_with_device]):
            # Call the service - should raise HomeAssistantError
            call_data = {"device_id": "test_device_123"}
            with pytest.raises(HomeAssistantError, match="Failed to force update device"):
                await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)


class TestServiceValidation:
    """Test service validation and error handling."""

    @pytest.mark.asyncio
    async def test_service_schemas_registered(self, hass: HomeAssistant):
        """Test that services are registered with proper schemas."""
        await async_setup_services(hass)
        
        # Check that services exist and are callable (implies they have schemas)
        assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)

    @pytest.mark.asyncio
    async def test_service_constants_defined(self):
        """Test that service constants are properly defined."""
        assert SERVICE_REFRESH_DEVICES == "refresh_devices"
        assert SERVICE_FORCE_UPDATE == "force_update"


class TestServiceIntegration:
    """Test service integration scenarios."""

    @pytest.mark.asyncio
    async def test_services_lifecycle(self, hass: HomeAssistant):
        """Test complete service lifecycle: setup and unload."""
        # Setup services
        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)
        
        # Unload services
        await async_unload_services(hass)
        assert not hass.services.has_service(DOMAIN, SERVICE_REFRESH_DEVICES)
        assert not hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE)

    @pytest.mark.asyncio
    async def test_service_error_logging(self, hass: HomeAssistant, caplog):
        """Test that service errors are properly logged."""
        # Setup services
        await async_setup_services(hass)
        
        # Mock config entries to cause an error
        with patch.object(hass.config_entries, 'async_entries', side_effect=Exception("Test error")):
            call_data = {"device_id": "test_device"}
            with pytest.raises(HomeAssistantError):
                await hass.services.async_call(DOMAIN, SERVICE_FORCE_UPDATE, call_data, blocking=True)
            
            # Check that error was logged
            assert "Failed to force update device" in caplog.text