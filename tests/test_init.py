"""Tests for Loca integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import pytest

from custom_components.loca import async_setup_entry, async_unload_entry
from custom_components.loca.const import DOMAIN


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(self, hass: HomeAssistant, mock_config_entry):
        """Test successful setup of config entry."""

        with patch(
            "custom_components.loca.LocaDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            # Mock the coordinator's first refresh
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()

            # Mock platform setup
            with patch.object(
                hass.config_entries, "async_forward_entry_setups"
            ) as mock_forward:
                mock_forward.return_value = True

                result = await async_setup_entry(hass, mock_config_entry)

                assert result is True

                # Check coordinator was created and configured
                mock_coordinator_class.assert_called_once_with(hass, mock_config_entry)
                mock_coordinator.async_config_entry_first_refresh.assert_called_once()

                # Check platforms were set up
                expected_platforms = [Platform.DEVICE_TRACKER, Platform.SENSOR]
                mock_forward.assert_called_once_with(
                    mock_config_entry, expected_platforms
                )

                # Check coordinator was stored in runtime_data (modern approach)
                assert mock_config_entry.runtime_data == mock_coordinator

    @pytest.mark.asyncio
    async def test_setup_entry_coordinator_first_refresh_fails(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test setup when coordinator first refresh fails."""

        with patch(
            "custom_components.loca.LocaDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            # Make first refresh fail
            mock_coordinator.async_config_entry_first_refresh.side_effect = Exception(
                "Refresh failed"
            )

            with pytest.raises(Exception, match="Refresh failed"):
                await async_setup_entry(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_platform_setup_fails(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test setup when platform setup fails."""

        with patch(
            "custom_components.loca.LocaDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()

            # Mock platform setup failure
            with patch.object(
                hass.config_entries, "async_forward_entry_setups"
            ) as mock_forward:
                mock_forward.side_effect = Exception("Platform setup failed")

                with pytest.raises(Exception, match="Platform setup failed"):
                    await async_setup_entry(hass, mock_config_entry)


class TestAsyncUnloadEntry:
    """Test the async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_unload_entry_success(self, hass: HomeAssistant, mock_config_entry):
        """Test successful unload of config entry."""

        # Set up runtime_data with a mock coordinator
        mock_coordinator = AsyncMock()
        mock_coordinator.async_shutdown = AsyncMock()
        mock_config_entry.runtime_data = mock_coordinator

        with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
            mock_unload.return_value = True

            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True

            # Check platforms were unloaded
            expected_platforms = [Platform.DEVICE_TRACKER, Platform.SENSOR]
            mock_unload.assert_called_once_with(mock_config_entry, expected_platforms)

            # Check coordinator shutdown was called
            mock_coordinator.async_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_entry_platform_unload_fails(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test unload when platform unload fails."""

        # Set up runtime_data with a mock coordinator
        mock_coordinator = AsyncMock()
        mock_coordinator.async_shutdown = AsyncMock()
        mock_config_entry.runtime_data = mock_coordinator

        with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
            mock_unload.return_value = False

            result = await async_unload_entry(hass, mock_config_entry)

            assert result is False

            # Check coordinator shutdown was not called when unload failed
            mock_coordinator.async_shutdown.assert_not_called()

    @pytest.mark.asyncio
    async def test_unload_entry_missing_coordinator(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test unload when coordinator is missing from runtime_data."""

        # Don't set up any coordinator in runtime_data
        mock_config_entry.runtime_data = None

        with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
            mock_unload.return_value = True

            # This should not raise an exception even if coordinator is missing
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_calls_coordinator_shutdown(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that coordinator shutdown is called during unload."""

        # Set up runtime_data with a mock coordinator that has async_shutdown
        mock_coordinator = AsyncMock()
        mock_coordinator.async_shutdown = AsyncMock()
        mock_config_entry.runtime_data = mock_coordinator

        with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
            mock_unload.return_value = True

            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True
            mock_coordinator.async_shutdown.assert_called_once()


class TestAsyncRemoveConfigEntryDevice:
    """Test async_remove_config_entry_device function."""

    @pytest.mark.asyncio
    async def test_remove_device_not_in_coordinator(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test removal is allowed when device is not in coordinator data."""
        from custom_components.loca import async_remove_config_entry_device

        mock_coordinator = AsyncMock()
        mock_coordinator.data = {"device_1": {"name": "Device 1"}}
        mock_config_entry.runtime_data = mock_coordinator

        # Create a device entry with an identifier NOT in coordinator data
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device_2")}

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, mock_device
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_device_still_in_coordinator(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test removal is denied when device is still in coordinator data."""
        from custom_components.loca import async_remove_config_entry_device

        mock_coordinator = AsyncMock()
        mock_coordinator.data = {"device_1": {"name": "Device 1"}}
        mock_config_entry.runtime_data = mock_coordinator

        # Create a device entry with an identifier that IS in coordinator data
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device_1")}

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, mock_device
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_device_empty_coordinator_data(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test removal is allowed when coordinator data is empty."""
        from custom_components.loca import async_remove_config_entry_device

        mock_coordinator = AsyncMock()
        mock_coordinator.data = {}
        mock_config_entry.runtime_data = mock_coordinator

        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device_1")}

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, mock_device
        )
        assert result is True


class TestConstants:
    """Test that required constants are defined."""

    def test_domain_constant(self):
        """Test that DOMAIN constant is properly defined."""
        assert DOMAIN == "loca"

    def test_platforms_constant(self):
        """Test that PLATFORMS constant includes expected platforms."""
        from custom_components.loca import PLATFORMS

        expected_platforms = [Platform.DEVICE_TRACKER, Platform.SENSOR]
        assert expected_platforms == PLATFORMS
