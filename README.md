# Loca Device Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/steynovich/ha-loca?style=for-the-badge)](https://github.com/steynovich/ha-loca/releases)
[![GitHub issues](https://img.shields.io/github/issues/steynovich/ha-loca?style=for-the-badge)](https://github.com/steynovich/ha-loca/issues)

A Home Assistant integration for tracking Loca GPS devices. This integration provides device tracking and sensor data for your Loca devices.

> **Current Status**: v1.1.4 includes improved error handling for API connectivity issues. The integration gracefully handles DNS timeouts and network errors without flooding logs with stack traces.

## Features

- **Device Tracking**: Track the location of your Loca GPS devices on the Home Assistant map
- **Comprehensive Sensors**: Multiple sensors for device monitoring:
  - Battery level monitoring
  - Location accuracy and GPS information
  - Current speed tracking
  - Last seen timestamps
  - Asset information (brand, model, type)
  - Location update configuration status
  - Human-readable address information
- **Multi-language Support**: Translations in 9 languages (EN, NL, DE, ES, FR, IT, PL, PT, SV)
- **Services**: Manual refresh and device update services
- **Diagnostics**: Comprehensive diagnostics for troubleshooting
- **Repairs**: Automatic issue detection and repair suggestions
- **Multiple Devices**: Support for multiple devices on one account
- **HACS Compatible**: Easy installation via HACS with zip releases

## Prerequisites

Before installing this integration, you need:

1. A Loca account with GPS tracking devices
2. API credentials from Loca:
   - API Key
   - Username
   - Password

Contact Loca support to obtain your API credentials.

## Installation

### Method 1: HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant
2. Go to HACS → Integrations
3. Click the three dots menu → Custom repositories
4. Add this repository URL: `https://github.com/steynovich/ha-loca`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Loca Device Tracker" and install it
8. Restart Home Assistant

### Method 2: Manual Installation

1. Download the latest release from the [releases page](https://github.com/steynovich/ha-loca/releases)
2. Extract the `custom_components/loca` folder to your Home Assistant `custom_components` directory
3. The final directory structure should look like:
   ```
   custom_components/
   └── loca/
       ├── __init__.py
       ├── config_flow.py
       ├── const.py
       ├── api.py
       ├── coordinator.py
       ├── device_tracker.py
       ├── sensor.py
       ├── services.py
       ├── diagnostics.py
       ├── repairs.py
       ├── services.yaml
       ├── manifest.json
       └── translations/
           ├── de.json
           ├── en.json
           ├── es.json
           ├── fr.json
           ├── it.json
           ├── nl.json
           ├── pl.json
           ├── pt.json
           └── sv.json
   ```
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Loca Device Tracker"
3. Enter your Loca API credentials:
   - **API Key**: Your Loca API key (obtained from Loca support)
   - **Username**: Your Loca account username
   - **Password**: Your Loca account password
4. Click **Submit**

The integration will automatically discover all devices associated with your account.

### Configuration Options

The integration supports the following configuration options:

#### API Settings
- **API Key** (required): Your unique Loca API key
  - Contact Loca support to obtain this key
  - Must be a valid alphanumeric string
- **Username** (required): Your Loca account username
  - Must match your registered Loca account
- **Password** (required): Your Loca account password
  - Must match your registered Loca account

#### Advanced Settings
- **Update Interval**: Device data refresh rate (default: 60 seconds)
  - Minimum recommended: 30 seconds
  - Maximum recommended: 300 seconds (5 minutes)
  - Lower values increase API usage but provide more frequent updates

#### Device Discovery
- The integration automatically discovers all GPS devices linked to your account
- Devices appear as both device trackers and sensors
- Device names are taken from your Loca device configuration
- If no name is set, devices use the format "Loca Device [ID]"

#### Supported Device Types
- All Loca GPS tracking devices
- Both personal and fleet tracking devices
- Devices with GPS and cellular (LBS) positioning

### Reconfiguration

To modify settings after initial setup:
1. Go to **Settings** → **Devices & Services**
2. Find your Loca integration
3. Click **Configure**
4. Update your credentials or settings
5. Click **Submit** to save changes

### Reauthentication

If your Loca credentials change or expire:
1. Home Assistant will automatically detect authentication failures
2. A notification will appear prompting you to update credentials
3. Click the notification and enter your new credentials
4. The integration will automatically reload with the new settings

### Multiple Accounts

You can add multiple Loca accounts:
1. Repeat the initial setup process
2. Each account creates a separate integration instance
3. Devices from different accounts are kept separate
4. Services can target specific accounts using config entry IDs

## Entities Created

For each Loca device, the integration creates:

### Device Tracker
- `device_tracker.loca_[device_name]` - Shows device location on the map

### Sensors
- `sensor.loca_[device_name]_battery` - Battery percentage (diagnostic)
- `sensor.loca_[device_name]_last_seen` - Last time the device reported its location (diagnostic)
- `sensor.loca_[device_name]_location_accuracy` - GPS accuracy in meters (diagnostic, disabled by default)
- `sensor.loca_[device_name]_asset_info` - Asset information with brand/model (diagnostic)
- `sensor.loca_[device_name]_speed` - Current speed in km/h
- `sensor.loca_[device_name]_location_update` - Location update configuration status (diagnostic)
- `sensor.loca_[device_name]_location` - Current location address

## Services

The integration provides the following services:

### `loca.refresh_devices`
Manually refresh device data from the Loca API for all or specific config entries.

**Parameters:**
- `config_entry_id` (optional): Specific config entry to refresh. If not provided, refreshes all Loca integrations.

**Example:**
```yaml
service: loca.refresh_devices
```

**Example with specific config entry:**
```yaml
service: loca.refresh_devices
data:
  config_entry_id: "abc123def456"
```

### `loca.force_update`  
Force an immediate update for a specific device by refreshing the coordinator containing that device.

**Parameters:**
- `device_id` (required): Device ID to update (found in device diagnostics or entity attributes)

**Example:**
```yaml
service: loca.force_update
data:
  device_id: "12345"
```

**Note**: Services are automatically registered when the integration is loaded and unregistered when unloaded.

## Automations Example

Here are some example automations you can create:

### Low Battery Alert
```yaml
automation:
  - alias: "Loca Device Low Battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.loca_device_battery
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "Loca device {{ trigger.to_state.attributes.friendly_name }} has low battery ({{ trigger.to_state.state }}%)"
```

### Device Offline Alert
```yaml
automation:
  - alias: "Loca Device Offline"
    trigger:
      - platform: template
        value_template: >
          {{ (now() - states.sensor.loca_device_last_seen.last_changed).total_seconds() > 3600 }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "Loca device has been offline for more than 1 hour"
```

## API Information

This integration uses the Loca API v1:
- **Base URL**: `https://api.loca.nl/v1/`
- **Authentication**: Session-based with API key
- **Update Interval**: 60 seconds (configurable)
- **Endpoints Used**:
  - `Login.json` - Authentication (returns user object)
  - `Assets.json` - Device information and locations
- **Response Format**: JSON with user object on successful login

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify your API key, username, and password are correct
   - Check that your Loca account is active  
   - Ensure API key has proper permissions (contact Loca support)
   - Check Home Assistant logs for detailed error messages
   - Try the test script: `python3 test_api.py` (in integration directory)
   - Verify internet connectivity and DNS resolution for api.loca.nl

2. **No Devices Found**
   - This is normal for new or empty Loca accounts
   - If you have devices, ensure they are properly set up and active
   - Check that devices are associated with your account in the Loca app/website
   - Verify devices are powered on and have GPS/cellular connectivity
   - Wait a few minutes after device setup for them to appear in the API

3. **Location Not Updating**
   - Check if the device has GPS signal
   - Verify the device battery is not low
   - Check device settings in the Loca app

### Debug Logging

To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.loca: debug
```

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/steynovich/ha-loca/issues) page.

For Loca API or account issues, contact [Loca Support](https://loca.nl/contact/).

## Diagnostics & Repairs

### Comprehensive Diagnostics
The integration provides detailed diagnostics for troubleshooting while protecting sensitive information:

**Config Entry Diagnostics:**
- Coordinator status and update intervals
- Device count and overview
- API connection status and configuration
- Sanitized configuration details
- Endpoint usage information

**Device Diagnostics:**
- Individual device status and capabilities
- Location and sensor data availability
- Entity status and expected entity count
- API attribute keys (values excluded for privacy)
- Battery and GPS accuracy information

**Privacy & Security Features:**
- **Credentials**: API keys, passwords, usernames masked as `***REDACTED***`
- **Location Privacy**: Exact coordinates excluded (only availability flags)
- **Sensitive Data**: Only configuration status and lengths provided
- **Raw API Data**: Key names only, no sensitive values

**Access**: Settings → Devices & Services → Loca → Device → Download Diagnostics

### Automatic Repairs
The integration includes a repairs system that automatically detects and suggests fixes for common issues:
- Authentication failures and credential problems
- API connectivity issues
- Device configuration problems
- Missing or invalid device data

**Access**: Settings → System → Repairs (issues appear automatically when detected)

## Development & Testing

### Project Structure

```
ha-loca/
├── .github/workflows/          # GitHub Actions CI/CD
│   ├── test.yml               # Automated testing
│   ├── validate.yml           # HACS validation
│   └── release.yml            # Release automation
├── assets/                    # Brand assets
│   ├── icon.svg              # Integration icon
│   └── logo.svg              # Integration logo
├── custom_components/loca/    # Main integration
│   ├── __init__.py           # Integration setup
│   ├── api.py                # Loca API client
│   ├── config_flow.py        # Configuration flow
│   ├── const.py              # Constants and mappings
│   ├── coordinator.py        # Data update coordinator
│   ├── device_tracker.py     # Device tracker platform
│   ├── sensor.py             # Sensor platform (7 sensor types)
│   ├── services.py           # Integration services
│   ├── diagnostics.py        # Diagnostics support
│   ├── repairs.py            # Repairs framework
│   ├── services.yaml         # Service definitions
│   ├── manifest.json         # Integration metadata
│   └── translations/         # Multi-language support
│       ├── de.json           # German
│       ├── en.json           # English (default)
│       ├── es.json           # Spanish
│       ├── fr.json           # French
│       ├── it.json           # Italian
│       ├── nl.json           # Dutch
│       ├── pl.json           # Polish
│       ├── pt.json           # Portuguese
│       └── sv.json           # Swedish
├── tests/                     # Comprehensive test suite
│   ├── conftest.py           # Test configuration
│   ├── test_*.py             # Test modules for each component
├── hacs.json                 # HACS configuration
├── requirements_test.txt     # Test dependencies
├── pytest.ini              # Pytest configuration
└── validate_*.py           # HACS compliance validation scripts
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=custom_components.loca --cov-report=html

# Run specific test categories
pytest tests/test_api.py          # API tests
pytest tests/test_sensor.py       # Sensor tests
pytest tests/test_config_flow.py  # Config flow tests

# Run with verbose output
pytest -v

# Run integration tests only
pytest -k "not unit"
```

### Test Coverage

The integration includes comprehensive tests covering:

**Core Functionality:**
- API client with authentication and session management
- Data coordinator with error handling and retry logic
- Config flow with validation and user feedback
- Device tracker entity with location mapping
- All 7 sensor types with proper state and attributes

**Advanced Features:**
- Services registration and execution
- Diagnostics data collection with privacy protection
- Repairs framework with issue detection
- Multi-language translation support
- HACS compliance validation

**Quality Assurance:**
- Integration setup and teardown procedures
- Error handling and edge cases
- Mock API responses and network failures
- Configuration validation and user input sanitization

### HACS Validation

Run HACS compliance checks:

```bash
# Basic compliance check
python validate_hacs_compliance.py

# Complete HACS validation
python validate_hacs_complete.py

# Test coverage validation
python validate_test_coverage.py

# Platinum quality validation
python validate_platinum.py
```

### Repository Topics

For HACS compatibility, ensure the GitHub repository has the following topics set:

**Required topics:**
- `home-assistant`
- `hacs`
- `integration`
- `loca`
- `device-tracker`
- `gps-tracking`

**Optional but recommended:**
- `home-assistant-component`
- `hacs-integration`
- `iot`
- `location-tracking`

**To set topics on GitHub:**
1. Go to your repository on GitHub
2. Click the gear icon next to "About" (top right)
3. Add topics in the "Topics" field
4. Click "Save changes"

**Via GitHub CLI:**
```bash
gh repo edit --add-topic home-assistant,hacs,integration,loca,device-tracker,gps-tracking
```

## Troubleshooting

### Authentication Issues

If you're experiencing authentication problems, especially after upgrading from v1.1.0:

#### Error: "name 'HTTPStatus' is not defined"
- **Solution**: Update to v1.1.1-alpha.1 or later
- **Cause**: Import conflict in v1.1.0 that has been fixed

#### Error: "object has no attribute 'last_update_success_time'"
- **Solution**: Update to v1.1.1-alpha.1 or later
- **Cause**: Coordinator attribute error in v1.1.0 that has been fixed

#### General Authentication Failures
1. **Verify Credentials**: Double-check your API key, username, and password
2. **Check API Status**: Ensure the Loca API is accessible
3. **Restart Integration**:
   - Go to Settings → Devices & Services
   - Find your Loca integration
   - Click the three dots → Reload
4. **Check Logs**: Look for detailed error messages in Home Assistant logs

#### Getting Help
- Check the [GitHub Issues](https://github.com/steynovich/ha-loca/issues) page
- Review [Release Notes](RELEASE_NOTES_v1.1.1-alpha.1.md) for known issues
- Enable debug logging for detailed troubleshooting

### Debug Logging

To enable detailed logging for troubleshooting:

```yaml
# Add to configuration.yaml
logger:
  default: info
  logs:
    custom_components.loca: debug
    custom_components.loca.api: debug
    custom_components.loca.coordinator: debug
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration for Loca devices. It is not affiliated with or endorsed by Loca BV.