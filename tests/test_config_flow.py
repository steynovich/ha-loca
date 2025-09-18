"""Tests for Loca config flow."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry  # type: ignore[import-untyped]

from custom_components.loca.config_flow import (
    CannotConnect,
    InvalidAuth,
    validate_input,
)
from custom_components.loca.const import CONF_API_KEY, DOMAIN


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setup entry."""
    with patch(
        "custom_components.loca.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


@pytest.fixture
def mock_loca_api() -> Generator[MagicMock, None, None]:
    """Mock Loca API."""
    with patch("custom_components.loca.config_flow.LocaAPI") as mock_class:
        mock_api = AsyncMock()
        mock_class.return_value = mock_api
        mock_api.authenticate = AsyncMock(return_value=True)
        mock_api.get_assets = AsyncMock(return_value=[
            {"id": "123", "name": "Test Device"}
        ])
        mock_api.close = AsyncMock()
        yield mock_api


@pytest.fixture
def user_input() -> dict[str, str]:
    """User input for config flow."""
    return {
        CONF_API_KEY: "test_api_key",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }


class TestConfigFlow:
    """Test the Loca config flow."""

    async def test_form_user(self, hass: HomeAssistant) -> None:
        """Test we get the form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}
        assert result["step_id"] == "user"

    async def test_form_user_success(
        self,
        hass: HomeAssistant,
        mock_loca_api: MagicMock,
        mock_setup_entry: AsyncMock,
        user_input: dict[str, str],
        expected_lingering_tasks,
    ) -> None:
        """Test successful user form submission."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )
        await hass.async_block_till_done()
        
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Loca (test_user)"
        assert result2["data"] == user_input
        
        mock_loca_api.authenticate.assert_called_once()
        mock_loca_api.get_assets.assert_called_once()
        mock_loca_api.close.assert_called_once()

    async def test_form_cannot_connect(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test we handle cannot connect error."""
        with patch("custom_components.loca.config_flow.validate_input") as mock_validate:
            mock_validate.side_effect = CannotConnect
            
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input,
            )
            
            assert result2["type"] is FlowResultType.FORM
            assert result2["errors"] == {"base": "cannot_connect"}

    async def test_form_invalid_auth(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test we handle invalid auth error."""
        with patch("custom_components.loca.config_flow.validate_input") as mock_validate:
            mock_validate.side_effect = InvalidAuth
            
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input,
            )
            
            assert result2["type"] is FlowResultType.FORM
            assert result2["errors"] == {"base": "invalid_auth"}

    async def test_form_unknown_error(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test we handle unknown error."""
        with patch("custom_components.loca.config_flow.validate_input") as mock_validate:
            mock_validate.side_effect = Exception("Unexpected error")
            
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input,
            )
            
            assert result2["type"] is FlowResultType.FORM
            assert result2["errors"] == {"base": "unknown"}

    async def test_form_already_configured(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test we abort if already configured."""
        import hashlib
        # Create unique_id that matches the new format with hash
        api_key_hash = hashlib.sha256(user_input[CONF_API_KEY].encode()).hexdigest()[:8]
        unique_id = f"{user_input[CONF_USERNAME]}_{api_key_hash}"
        
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=unique_id,
            data=user_input,
        )
        existing_entry.add_to_hass(hass)
        
        with patch("custom_components.loca.config_flow.validate_input") as mock_validate:
            mock_validate.return_value = {"title": "Loca (test_user)"}
            
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input,
            )
            
            assert result2["type"] is FlowResultType.ABORT
            assert result2["reason"] == "already_configured"


class TestValidateInput:
    """Test the validate_input function."""

    async def test_validate_input_success(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
        mock_loca_api: MagicMock,
    ) -> None:
        """Test successful input validation."""
        result = await validate_input(hass, user_input)
        
        assert result == {"title": "Loca (test_user)"}
        mock_loca_api.authenticate.assert_called_once()
        mock_loca_api.get_assets.assert_called_once()
        mock_loca_api.close.assert_called_once()

    async def test_validate_input_auth_failure(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test validation with authentication failure."""
        with patch("custom_components.loca.config_flow.LocaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.authenticate.side_effect = Exception("Auth failed")
            mock_api.close = AsyncMock()
            
            with pytest.raises(CannotConnect):
                await validate_input(hass, user_input)
            
            mock_api.close.assert_called_once()

    async def test_validate_input_no_auth(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test validation when authentication returns False."""
        with patch("custom_components.loca.config_flow.LocaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.authenticate.return_value = False
            mock_api.close = AsyncMock()
            
            with pytest.raises(InvalidAuth):
                await validate_input(hass, user_input)
            
            mock_api.close.assert_called_once()

    async def test_validate_input_no_devices(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test validation with no devices (should succeed)."""
        with patch("custom_components.loca.config_flow.LocaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.authenticate.return_value = True
            mock_api.get_assets.return_value = []
            mock_api.close = AsyncMock()
            
            result = await validate_input(hass, user_input)
            assert result["title"] == "Loca (test_user)"
            
            mock_api.close.assert_called_once()

    async def test_validate_input_closes_api_on_exception(
        self,
        hass: HomeAssistant,
        user_input: dict[str, str],
    ) -> None:
        """Test that API is closed even when exception occurs."""
        with patch("custom_components.loca.config_flow.LocaAPI") as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            mock_api.authenticate.return_value = True
            mock_api.get_assets.side_effect = Exception("Network error")
            mock_api.close = AsyncMock()
            
            with pytest.raises(CannotConnect):
                await validate_input(hass, user_input)
            
            mock_api.close.assert_called_once()


class TestConfigFlowOptions:
    """Test config flow options."""

    async def test_options_flow_init(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test options flow initialization."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="test_user",
            data={
                CONF_API_KEY: "test_key",
                CONF_USERNAME: "test_user",
                CONF_PASSWORD: "test_pass",
            },
        )
        entry.add_to_hass(hass)
        
        # Register the config flow
        with patch("custom_components.loca.async_setup_entry", return_value=True):
            result = await hass.config_entries.options.async_init(entry.entry_id)
        
        # The options flow should show a form
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"


