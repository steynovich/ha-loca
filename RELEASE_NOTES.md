# Release Notes

All versions of the Loca Device Tracker integration for Home Assistant.

## Version History

- [v2.0.0](#v200---python-314--ha-20263-baseline) - Current
- [v1.1.1-alpha.1](#v111-alpha1---critical-authentication-fixes) (Alpha)
- [v1.0.3](#v103---security-update)
- [v1.0.2](#v102---critical-bug-fixes--security-improvements)
- [v1.0.1](#v101---bug-fix-release)
- [v1.0.0](#v100---initial-release)

---

# v2.0.0 - Python 3.14 / HA 2026.3 baseline

**Release Date**: 2026-04-15

## ⚠️ Breaking Changes

- **Minimum Home Assistant version: 2026.3.0** (matches HA's switch to Python 3.14).
  Installs on HA 2025.x / Python 3.13 are no longer supported.
- **Minimum Python version: 3.14** for development and CI.

## 🛠 Fixes

- **Options changes now apply automatically.** The config-entry update listener
  was defined but never registered, so `scan_interval` (and any future option)
  had no effect without a manual reload. Now wired via
  `entry.add_update_listener(async_reload_entry)`.
- **Silent failure on session expiry is fixed.** Authenticated data-endpoint
  calls (`Assets.json`, `StatusList.json`, `UserLocationList.json`,
  `Groups.json`) now retry once after re-authenticating when the server
  responds with HTTP 401/403, instead of returning empty data and leaving
  `is_authenticated == True`.
- **Repairs flow now targets the correct entry.** The auth-failed issue
  carries `entry_id` through to the flow, so users with multiple Loca accounts
  see the *right* account's reauth dialog.
- **`validate_input` no longer mislabels programming errors as "cannot
  connect".** Only `LocaAPIUnavailableError` is wrapped as `CannotConnect`;
  unexpected exceptions propagate to the caller's `unknown` branch.

## 🧹 Cleanup

- Removed `aiohttp` from `manifest.json` requirements (HA core bundles it —
  listing it violates HA integration rules).
- Deleted stale `VERSION` file, duplicate root `services.yaml`, and
  stand-alone `pytest.ini` / `mypy.ini`. All config now lives in
  `pyproject.toml`.
- Removed dead `"attributes"` payload (written every poll, never read),
  unreachable `gps_accuracy` fallback, and an unused
  `mock_status_list_data` fixture.
- Fixed variable shadowing in `async_unload_entry`.
- Fixed broken reference to the removed `parse_device_data` method in the
  root `test_api.py` debug script.
- Ruff/mypy/ruff-format now target Python 3.14; applied PEP 758
  (parenthesis-free `except`) where appropriate.

## 📦 Tooling

- CI `DEFAULT_PYTHON` bumped to `3.14`.
- `hacs.json` `render_readme` removed (deprecated by HACS).
- Local dev workflow documented with `uv` (CI still uses pip).

## Verification

- `ruff check` + `ruff format --check` clean
- `mypy --explicit-package-bases custom_components/loca tests/` — clean
- `pytest` — 264 passed (added one test asserting unexpected exceptions
  propagate through the config flow)
- HACS validation scripts — all pass

---

# v1.1.1-alpha.1 - Critical Authentication Fixes

**Release Date**: Alpha Release

## 🚨 Critical Bug Fixes

This alpha release addresses critical authentication and entity registration issues that broke the integration in v1.1.0.

### Fixed Issues

#### Authentication Failures
- **Fixed HTTPStatus import conflict**: Resolved `NameError: name 'HTTPStatus' is not defined` that prevented API authentication
- **Fixed coordinator attribute error**: Resolved `AttributeError: 'LocaDataUpdateCoordinator' object has no attribute 'last_update_success_time'` that prevented entity registration

#### Technical Details
- **Import Resolution**: Removed conflicting `http.HTTPStatus` import and properly used the local `HTTPStatus` class from constants
- **Cache Management**: Updated entity data caching to use object identity tracking instead of timestamp-based invalidation
- **Code Quality**: Fixed 44 linting issues and maintained full type safety with mypy

## 🔧 Technical Improvements

### Code Quality
- **Linting**: All ruff checks now pass (fixed unused imports, style issues)
- **Type Safety**: Full mypy compliance across all 25 source files
- **Import Optimization**: Cleaned up unused imports across the codebase

### Error Handling
- Improved error handling in the base entity mixin
- Better cache invalidation logic for entity data
- More robust coordinator integration

## 🧪 Testing

- ✅ All 29 API tests pass
- ✅ All 29 sensor tests pass
- ✅ All integration tests pass
- ✅ Full type checking compliance
- ✅ Zero linting issues

## 🚀 Installation

This is an alpha release. To install:

### Manual Installation
1. Download the `loca` folder from this release
2. Copy it to your `config/custom_components/` directory
3. Restart Home Assistant
4. Reconfigure the integration if authentication was failing

### HACS Installation
*Alpha releases are not available through HACS*

## ⚠️ Breaking Changes

None - this release only fixes existing functionality.

## 📋 Requirements

- Home Assistant 2024.1.0 or newer
- Loca API credentials (API key, username, password)
- Active Loca device subscription

## 🐛 Known Issues

- This is an alpha release - please report any issues on GitHub
- Test cleanup may show warnings (framework issue, not affecting functionality)

## 🔄 Migration from v1.1.0

If you experienced authentication failures with v1.1.0:
1. Update to v1.1.1-alpha.1
2. Restart Home Assistant
3. The integration should authenticate successfully
4. All entities should be created properly

## 🤝 Contributing

Found a bug? Please report it on our [GitHub Issues](https://github.com/steynovich/ha-loca/issues) page.

---

**Full Changelog**: v1.1.0...v1.1.1-alpha.1
- 945371b Fix mypy type errors across multiple modules

**Compatibility**: Home Assistant 2024.1.0+

**Status**: Alpha Release - Use with caution

---

# v1.0.3 - Security Update

## 🔒 Security Fixes

This release addresses important security vulnerabilities discovered during a security audit.

### High Severity
- **Fixed GPS coordinate exposure in diagnostics**
  - GPS coordinates (latitude/longitude) are now properly redacted in diagnostic outputs
  - Address fields are also redacted to prevent location disclosure
  - Added `has_gps_data` boolean flag to indicate GPS availability without exposing coordinates
  - This prevents potential privacy breaches when users share diagnostic files for support

### Medium Severity
- **Fixed partial API key disclosure**
  - Unique IDs now use SHA256 hash instead of raw API key characters
  - Removed API key and username length information from diagnostics
  - This prevents potential credential attacks from partial key exposure

## 🔧 Technical Changes

**Modified Files:**
- `custom_components/loca/diagnostics.py` - Redact sensitive location data
- `custom_components/loca/config_flow.py` - Use hash for unique ID generation
- `tests/test_diagnostics.py` - Update tests for redacted data
- `tests/test_config_flow.py` - Update tests for new unique ID format

## 📋 Testing

All existing tests have been updated and are passing:
- Configuration flow tests updated for new unique ID format
- Diagnostic tests updated to verify proper data redaction
- Full test suite passes with 100% compatibility

## 🔄 Compatibility

This update is fully backward compatible. No configuration changes are required.

## 📝 Recommendations

Users are strongly encouraged to update to this version to protect their location privacy and credential security.

---

**Full Changelog:** [v1.0.2...v1.0.3](https://github.com/steynovich/ha-loca/compare/v1.0.2...v1.0.3)

---

# v1.0.2 - Critical Bug Fixes & Security Improvements

## 🐛 Critical Bug Fixes

### Security & Stability Improvements
- **Fixed**: Removed unsafe cookie jar configuration that could pose security risks
- **Fixed**: Memory leak risk in API client session handling
- **Fixed**: Race condition in service registration that could cause duplicate service registration
- **Fixed**: Race condition in entity management during concurrent operations

### Data Integrity Fixes
- **Fixed**: Inconsistent timezone handling causing datetime comparison issues
- **Fixed**: Potential division by zero in sensor time parsing that could cause crashes
- **Fixed**: Missing null checks for datetime objects preventing proper error handling
- **Fixed**: Config flow unique ID collision when using multiple accounts with same username

### Code Quality Improvements
- **Fixed**: Direct access to private API authentication state
- **Removed**: Unused `parse_device_data` method reducing code complexity

## 🔧 Technical Improvements

### API Client Updates
- Improved session management to prevent memory leaks
- Added public `is_authenticated` property for proper state access
- Ensured consistent UTC timezone usage across all datetime operations
- Removed unsafe cookie jar configuration

### Entity Management
- Added documentation for Home Assistant's dynamic entity limitations
- Improved null safety checks for datetime objects
- Added safe division guards in time parsing logic

### Configuration Flow
- Improved unique ID generation using username + API key prefix
- Better support for multiple Loca accounts on same Home Assistant instance

## 📋 Requirements

No changes from v1.0.1:
- Home Assistant 2024.1.0 or newer
- Loca API credentials (API key, username, password)
- Active Loca device subscription

## 🚀 Upgrading

Simply update the integration through HACS or manually replace the `loca` folder in your `custom_components` directory and restart Home Assistant.

## 🔄 Changes from v1.0.1

### Fixed
- Security vulnerability with unsafe cookie jar
- Memory leak in session management
- Race conditions in service and entity management
- Timezone inconsistencies in datetime handling
- Division by zero crashes in sensor parsing
- Config entry unique ID collisions
- Null reference exceptions with datetime objects

### Improved
- Code quality and maintainability
- Error handling and stability
- Support for multiple accounts

### Removed
- Unused code reducing maintenance burden

## 📝 Full Changelog

**Security**
- Removed unsafe cookie jar configuration

**Fixed**
- Memory leak risk in ClientSession handling
- Race condition in service registration
- Race condition in entity management
- Inconsistent UTC timezone usage
- Potential division by zero in time parsing
- Null safety for datetime operations
- Config flow unique ID generation
- Private API state access pattern

**Removed**
- Unused `parse_device_data` method

**Testing**
- Fixed test suite compatibility with refactored code
- Updated test fixtures for new API signature
- Improved test coverage for session management

---

**Compatibility**: Home Assistant 2024.1.0+

**Tested with**: Home Assistant 2024.12.0

---

# v1.0.1 - Bug Fix Release

## 🐛 Bug Fixes

### Fixed Home Assistant aiohttp Session Warning
- **Issue**: Integration was creating and closing its own aiohttp session, triggering Home Assistant warnings about closing the shared session
- **Solution**: Updated to properly use Home Assistant's shared aiohttp session via `aiohttp_client`
- **Impact**: Eliminates warning messages in logs and ensures proper resource management

## 🔧 Technical Improvements

### API Client Updates
- Modified `LocaAPI` class to accept `HomeAssistant` instance for proper session management
- Session is now obtained from `aiohttp_client.async_get_clientsession(hass)`
- Session cleanup only occurs in standalone/testing scenarios (when `hass` is None)

### Integration Points Updated
- `DataUpdateCoordinator` now passes `hass` instance to `LocaAPI`
- `ConfigFlow` properly initializes API client with `hass` reference
- Maintains backward compatibility for testing scenarios

## 📋 Requirements

No changes from v1.0.0:
- Home Assistant 2024.1.0 or newer
- Loca API credentials (API key, username, password)
- Active Loca device subscription

## 🚀 Upgrading

Simply update the integration through HACS or manually replace the `loca` folder in your `custom_components` directory and restart Home Assistant.

## 🔄 Changes from v1.0.0

- Fixed aiohttp session warning by using Home Assistant's shared session
- Improved resource management and integration stability
- No breaking changes or configuration updates required

## 📝 Full Changelog

**Fixed**
- Home Assistant aiohttp session warning when closing shared session

**Changed**
- API client now uses Home Assistant's shared aiohttp session
- Session management aligned with Home Assistant best practices

---

**Compatibility**: Home Assistant 2024.1.0+

**Tested with**: Home Assistant 2024.12.0

---

# v1.0.0 - Initial Release

## 🎉 First Stable Release

This is the first stable release of the **Loca Device Tracker** integration for Home Assistant, providing comprehensive GPS tracking capabilities for Loca devices.

## ✨ Features

### Core Functionality
- **Real-time GPS Tracking** - Monitor device locations with automatic updates
- **Battery Monitoring** - Track battery levels of your Loca devices
- **Multiple Sensor Types**:
  - Battery level sensor
  - Last seen timestamp
  - GPS accuracy indicator
- **Automatic Device Discovery** - Seamlessly detects all devices in your Loca account
- **Multi-device Support** - Track unlimited Loca devices simultaneously

### Advanced Features
- **Zone Integration** - Full compatibility with Home Assistant zones
- **Detailed Attributes**:
  - Current speed
  - Number of satellites
  - Full address information
  - Signal strength
  - Device group information
- **Diagnostics Support** - Built-in troubleshooting capabilities
- **Repair Flows** - Automated fixes for common configuration issues
- **Service Calls**:
  - `loca.refresh_devices` - Manual device refresh
  - `loca.force_update` - Force update specific device

## 📋 Requirements

- Home Assistant 2024.1.0 or newer
- Loca API credentials:
  - API key
  - Username
  - Password
- Active Loca device subscription

## 🚀 Installation

### HACS (Recommended)
*Coming soon*

### Manual Installation
1. Download the `loca` folder from this release
2. Copy it to your `config/custom_components/` directory
3. Restart Home Assistant
4. Navigate to **Settings** → **Devices & Services**
5. Click **+ Add Integration**
6. Search for "Loca"
7. Enter your Loca API credentials

## 🔧 Configuration

The integration is configured through the UI. You'll need:
- **API Key**: Your Loca API key (found in your Loca account)
- **Username**: Your Loca account username
- **Password**: Your Loca account password

## 📊 Provided Entities

For each Loca device, the following entities are created:
- `device_tracker.<device_name>` - Primary tracking entity
- `sensor.<device_name>_battery` - Battery level (%)
- `sensor.<device_name>_last_seen` - Last update timestamp
- `sensor.<device_name>_location_accuracy` - GPS accuracy (meters)

## 🐛 Known Issues

- Test cleanup may show warnings (framework issue, not affecting functionality)
- Some devices may show "Unknown" for certain attributes if not supported by the device

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Home Assistant community for the amazing platform
- Loca for providing the GPS tracking service and API

---

**Full Changelog**: Initial release

**Compatibility**: Home Assistant 2024.1.0+

**Tested with**: Home Assistant 2024.12.0
