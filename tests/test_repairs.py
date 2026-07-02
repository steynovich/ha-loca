"""Tests for Loca repairs functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest

from custom_components.loca.const import DOMAIN
from custom_components.loca.repairs import (
    ApiAuthenticationFailedRepairFlow,
    DeprecatedYamlConfigurationRepairFlow,
    NoDevicesFoundRepairFlow,
    async_create_api_auth_issue,
    async_create_fix_flow,
    async_create_issue,
    async_create_no_devices_issue,
)


class TestRepairFlows:
    """Test repair flow classes."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            "api_key": "test_key",
            "username": "test_user",
            "password": "test_pass",
        }
        return entry

    @pytest.mark.asyncio
    async def test_no_devices_flow_init(self, mock_hass, mock_config_entry):
        """Test NoDevicesFoundRepairFlow initialization."""
        flow = NoDevicesFoundRepairFlow()
        flow.hass = mock_hass

        result = await flow.async_step_init()

        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert "description_placeholders" in result

    @pytest.mark.asyncio
    async def test_api_auth_flow_init(self, mock_hass, mock_config_entry):
        """Test ApiAuthenticationFailedRepairFlow initialization."""
        flow = ApiAuthenticationFailedRepairFlow()
        flow.hass = mock_hass

        result = await flow.async_step_init()

        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert "description_placeholders" in result

    @pytest.mark.asyncio
    async def test_api_auth_flow_reauth_success(self, mock_hass, mock_config_entry):
        """Test API auth flow reauth success."""
        flow = ApiAuthenticationFailedRepairFlow()
        flow.hass = mock_hass

        with patch.object(
            mock_hass.config_entries, "async_entries", return_value=[mock_config_entry]
        ):
            with patch.object(mock_hass, "async_create_task") as mock_create_task:
                result = await flow.async_step_init({"confirm": "true"})

                assert result["type"] == "create_entry"
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_deprecated_yaml_flow_init(self, mock_hass, mock_config_entry):
        """Test DeprecatedYamlConfigurationRepairFlow initialization."""
        flow = DeprecatedYamlConfigurationRepairFlow()
        flow.hass = mock_hass

        result = await flow.async_step_init()

        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert "description_placeholders" in result


class TestRepairFlowCreation:
    """Test repair flow creation functions."""

    @pytest.mark.asyncio
    async def test_create_fix_flow_no_devices(self, hass: HomeAssistant):
        """Test creating fix flow for no devices issue."""
        flow = await async_create_fix_flow(hass, "no_devices_found", {})

        assert isinstance(flow, NoDevicesFoundRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_api_auth(self, hass: HomeAssistant):
        """Test creating fix flow for API auth issue."""
        flow = await async_create_fix_flow(hass, "api_authentication_failed", {})

        assert isinstance(flow, ApiAuthenticationFailedRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_deprecated_yaml(self, hass: HomeAssistant):
        """Test creating fix flow for deprecated yaml issue."""
        flow = await async_create_fix_flow(hass, "deprecated_yaml_configuration", {})

        assert isinstance(flow, DeprecatedYamlConfigurationRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_unknown_issue(self, hass: HomeAssistant):
        """Test creating fix flow for unknown issue returns ConfirmRepairFlow."""
        from homeassistant.components.repairs import ConfirmRepairFlow

        flow = await async_create_fix_flow(hass, "unknown_issue", {})

        assert isinstance(flow, ConfirmRepairFlow)


class TestIssueCreation:
    """Test issue creation functions."""

    @pytest.fixture
    def mock_issue_registry(self):
        """Create a mock issue registry."""
        registry = MagicMock()
        registry.async_create_issue = AsyncMock()
        registry.async_delete_issue = AsyncMock()
        return registry

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {"username": "test@example.com"}
        entry.title = "test@example.com"
        return entry

    @pytest.mark.asyncio
    async def test_create_issue_generic(self, hass: HomeAssistant, mock_config_entry):
        """Test generic issue creation."""
        with patch(
            "custom_components.loca.repairs.ir.async_create_issue"
        ) as mock_create_issue:
            async_create_issue(
                hass,
                "test_issue",
                "test_issue",
                {"account": "test@example.com"},
                ir.IssueSeverity.ERROR,
            )

            mock_create_issue.assert_called_once_with(
                hass,
                DOMAIN,
                "test_issue",
                is_fixable=True,
                severity=ir.IssueSeverity.ERROR,
                translation_key="test_issue",
                translation_placeholders={"account": "test@example.com"},
                data=None,
            )

    @pytest.mark.asyncio
    async def test_create_no_devices_issue(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test no devices issue creation."""
        with patch("custom_components.loca.repairs.async_create_issue") as mock_create:
            async_create_no_devices_issue(hass, mock_config_entry)

            mock_create.assert_called_once_with(
                hass,
                f"no_devices_found_{mock_config_entry.entry_id}",
                "no_devices_found",
                translation_placeholders={"account": mock_config_entry.title},
                severity=ir.IssueSeverity.WARNING,
                data={"entry_id": mock_config_entry.entry_id},
            )

    @pytest.mark.asyncio
    async def test_create_api_auth_issue(self, hass: HomeAssistant, mock_config_entry):
        """Test API auth issue creation."""
        with patch("custom_components.loca.repairs.async_create_issue") as mock_create:
            async_create_api_auth_issue(hass, mock_config_entry)

            mock_create.assert_called_once_with(
                hass,
                f"api_authentication_failed_{mock_config_entry.entry_id}",
                "api_authentication_failed",
                translation_placeholders={"account": mock_config_entry.title},
                severity=ir.IssueSeverity.ERROR,
                data={"entry_id": mock_config_entry.entry_id},
            )


class TestIssueScoping:
    """Test that repair issues are scoped per config entry.

    Regression tests: one account's successful poll must not dismiss another
    account's still-active repair issue.
    """

    def _make_entry(self, entry_id: str) -> MagicMock:
        entry = MagicMock()
        entry.entry_id = entry_id
        entry.title = f"account-{entry_id}"
        return entry

    @pytest.mark.asyncio
    async def test_auth_issue_scoped_per_entry(self, hass: HomeAssistant):
        """Test deleting entry B's auth issue leaves entry A's issue intact."""
        from custom_components.loca.repairs import async_delete_api_auth_issue

        entry_a = self._make_entry("entry_a")
        entry_b = self._make_entry("entry_b")

        async_create_api_auth_issue(hass, entry_a)

        registry = ir.async_get(hass)
        issue_a_id = f"api_authentication_failed_{entry_a.entry_id}"
        assert registry.async_get_issue(DOMAIN, issue_a_id) is not None

        # Entry B's successful poll deletes only its own issue
        async_delete_api_auth_issue(hass, entry_b)
        assert registry.async_get_issue(DOMAIN, issue_a_id) is not None

        # Entry A's own success clears it
        async_delete_api_auth_issue(hass, entry_a)
        assert registry.async_get_issue(DOMAIN, issue_a_id) is None

    @pytest.mark.asyncio
    async def test_no_devices_issue_scoped_per_entry(self, hass: HomeAssistant):
        """Test deleting entry B's no-devices issue leaves entry A's intact."""
        from custom_components.loca.repairs import async_delete_no_devices_issue

        entry_a = self._make_entry("entry_a")
        entry_b = self._make_entry("entry_b")

        async_create_no_devices_issue(hass, entry_a)

        registry = ir.async_get(hass)
        issue_a_id = f"no_devices_found_{entry_a.entry_id}"
        assert registry.async_get_issue(DOMAIN, issue_a_id) is not None

        async_delete_no_devices_issue(hass, entry_b)
        assert registry.async_get_issue(DOMAIN, issue_a_id) is not None

        async_delete_no_devices_issue(hass, entry_a)
        assert registry.async_get_issue(DOMAIN, issue_a_id) is None

    @pytest.mark.asyncio
    async def test_create_fix_flow_matches_scoped_issue_ids(self, hass: HomeAssistant):
        """Test the fix-flow factory resolves entry-suffixed issue IDs."""
        from custom_components.loca.repairs import (
            ApiAuthenticationFailedRepairFlow,
            NoDevicesFoundRepairFlow,
            async_create_fix_flow,
        )

        auth_flow = await async_create_fix_flow(
            hass,
            "api_authentication_failed_entry_a",
            {"entry_id": "entry_a"},
        )
        assert isinstance(auth_flow, ApiAuthenticationFailedRepairFlow)

        devices_flow = await async_create_fix_flow(
            hass, "no_devices_found_entry_a", {"entry_id": "entry_a"}
        )
        assert isinstance(devices_flow, NoDevicesFoundRepairFlow)


class TestRepairErrorHandling:
    """Test error handling in repair functionality."""

    @pytest.mark.asyncio
    async def test_flow_handles_missing_config_entry(self, hass: HomeAssistant):
        """Test that flows handle missing config entry gracefully."""
        flow = NoDevicesFoundRepairFlow()
        flow.hass = hass

        result = await flow.async_step_init()

        # Should still return a form, but may have different placeholders
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_issue_creation_with_registry_error(self, hass: HomeAssistant):
        """Test issue creation when registry has errors."""
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test"
        mock_config_entry.data = {"username": "test"}

        with patch(
            "custom_components.loca.repairs.ir.async_create_issue"
        ) as mock_create_issue:
            mock_create_issue.side_effect = Exception("Registry error")

            # Should raise exception since async_create_issue doesn't handle errors
            with pytest.raises(Exception, match="Registry error"):
                async_create_issue(hass, "test", "test", {})


class TestRepairIntegration:
    """Test integration between repairs and main components."""

    @pytest.mark.asyncio
    async def test_repair_triggered_by_coordinator_error(self):
        """Test that repairs are triggered by coordinator errors."""
        # This would test the integration with coordinator.py
        # where repairs are actually triggered

    @pytest.mark.asyncio
    async def test_repair_resolves_when_issue_fixed(self):
        """Test that repair issues are resolved when problem is fixed."""
        # This would test that issues are automatically deleted
        # when the underlying problem is resolved
