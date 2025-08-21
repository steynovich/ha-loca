"""Common fixtures for Loca tests."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.loca.const import CONF_API_KEY, DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for tests."""
    yield


@pytest.fixture
def expected_lingering_tasks():
    """Fixture to allow expected lingering tasks."""
    return True


@pytest.fixture  
def expected_lingering_timers():
    """Fixture to allow expected lingering timers."""
    return True


@pytest.fixture(autouse=True)
def mock_persistent_notification():
    """Mock persistent notification to avoid warnings in tests."""
    with patch("homeassistant.components.persistent_notification"):
        yield


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Loca",
        data={
            CONF_API_KEY: "test_api_key",
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        },
        options={},
        source="user",
        entry_id="test_entry_id",
        discovery_keys=set(),
        unique_id="test_user",
    )


@pytest.fixture
def mock_api_data():
    """Return mock API data."""
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
                    "time": 1640995200,  # 2022-01-01 00:00:00
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
                    "time": 1640995260,  # 2022-01-01 00:01:00
                    "accuracy": 10,
                    "origin": 2,
                },
            },
        ],
    }


@pytest.fixture
def mock_status_list_data():
    """Return mock StatusList API data."""
    return [
        {
            "asset_id": "12345",
            "asset_label": "Test Device",
            "latitude": "52.3676",
            "longitude": "4.9041",
            "street": "Test Street",
            "number": "42",
            "city": "Amsterdam",
            "zipcode": "1234AB",
            "country": "Netherlands",
            "gps_accuracy": "5",
            "timestamp": "2022-01-01 00:00:00",
            "speed": "65.5",
            "satellites": "8",
            "battery": "85",
            "asset_info": {
                "type": 1,
                "brand": "BMW",
                "model": "X3",
                "serial": "ABC123",
                "group": 248,
            },
        },
        {
            "asset_id": "67890",
            "asset_label": "Second Device",
            "latitude": "51.5074",
            "longitude": "-0.1278",
            "gps_accuracy": "10",
            "timestamp": "2022-01-01 00:01:00",
            "battery": "42",
        },
    ]


@pytest.fixture
def mock_empty_response():
    """Return mock empty API response."""
    return {
        "status": "ok",
        "assets": [],
    }


@pytest.fixture
def mock_error_response():
    """Return mock error API response."""
    return {
        "status": "error",
        "message": "Authentication failed",
    }


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.last_exception = None
    return coordinator


@pytest.fixture
def mock_coordinator_with_data(mock_status_list_data):
    """Create a mock coordinator with data."""
    from datetime import datetime
    
    coordinator = MagicMock()
    coordinator.data = {
        "12345": {
            "device_id": "12345",
            "name": "Test Device",
            "latitude": 52.3676,
            "longitude": 4.9041,
            "battery_level": 85,
            "gps_accuracy": 5,
            "location_source": "GPS",
            "last_seen": datetime(2022, 1, 1, 0, 0, 0),
            "address": "Test Street 42, 1234AB Amsterdam, Netherlands",
            "speed": 65.5,
            "satellites": 8,
            "asset_info": {
                "type": 1,
                "brand": "BMW",
                "model": "X3",
                "serial": "ABC123",
                "group": 248,
                "group_name": "Autos",
            },
        },
        "67890": {
            "device_id": "67890",
            "name": "Second Device",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "battery_level": 42,
            "gps_accuracy": 10,
            "location_source": "Cell Tower",
            "last_seen": datetime(2022, 1, 1, 0, 1, 0),
        },
    }
    coordinator.last_update_success = True
    coordinator.last_exception = None
    return coordinator