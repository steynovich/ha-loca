# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2025-11-27

### Improved Error Handling

This release significantly improves how the integration handles API connectivity issues, reducing log noise and improving reliability.

#### API Connectivity Improvements
- **New**: Graceful handling of DNS timeouts, connection refused, and network errors
  - No more stack traces in logs for temporary connectivity issues
  - Clean warning messages: "Get assets failed: Cannot connect to Loca API (network/DNS issue). Will retry on next update cycle."
  - Automatic retry on next update cycle
- **New**: Added 30-second timeout protection on all API calls
  - Prevents indefinite hangs when API is unresponsive
  - Proper `TimeoutError` handling with user-friendly messages
- **New**: `LocaAPIUnavailableError` exception for clear API unavailability signaling

#### Code Quality Improvements
- **Fixed**: Race condition in service registration using proper service existence check
- **Fixed**: Cache invalidation in entity mixin now uses `last_update_success_time` instead of `id()` (which can be reused by Python GC)
- **Fixed**: Sensitive data no longer logged in API error responses
- **Improved**: Service error handling now distinguishes between connectivity, update, and validation errors
- **Improved**: Consolidated timestamp parsing to handle both Unix timestamps and ISO format strings
- **Improved**: Added coordinate validation using `DataValidator` in all parsing methods
- **Improved**: Added public API properties (`has_credentials`, `groups_cache_size`) for diagnostics
- **Removed**: Unused `parallel_updates` semaphore declarations from sensor and device tracker

#### New Test Coverage
- Added comprehensive tests for error handling module (`test_error_handling.py`)
- Added validation edge case tests (`test_validation.py`)
- Added API connectivity error tests (DNS, timeout, connection refused)
- Added HTTP status code tests (403, 404, 429, 503)
- Added coordinator error handling tests
- Added service-specific error tests
- Added timestamp parsing tests for multiple formats

### Technical Details
- Modified Files:
  - `custom_components/loca/api.py` - Timeout protection, connectivity error handling, consolidated timestamp parsing
  - `custom_components/loca/coordinator.py` - LocaAPIUnavailableError handling
  - `custom_components/loca/error_handling.py` - New connectivity error utilities
  - `custom_components/loca/services.py` - Improved exception handling
  - `custom_components/loca/__init__.py` - Fixed service registration race condition
  - `custom_components/loca/base.py` - Fixed cache invalidation
  - `custom_components/loca/const.py` - Added API_TIMEOUT constant
  - `custom_components/loca/diagnostics.py` - Uses public API properties
  - `custom_components/loca/sensor.py` - Removed unused imports
  - `custom_components/loca/device_tracker.py` - Removed unused imports
- New Test Files:
  - `tests/test_error_handling.py` - Error handling utilities
  - `tests/test_validation.py` - Data validation edge cases
- All tests pass with ruff and mypy compliance

---

## [1.1.2] - 2025-11-24

### Bug Fixes

#### Sensor Availability Logic (Medium Severity)
- **Fixed**: Sensors incorrectly showing as "unavailable" when their value was `None`
  - Battery, speed, last seen, and location accuracy sensors now correctly show as available even when their values are legitimately `None`
  - Previously, sensors would appear unavailable in Home Assistant UI even though the device was present
  - This caused false "unknown" states and broke automations depending on sensor availability

#### Service Exception Handling (Low Severity)
- **Fixed**: Potential `UnboundLocalError` in force update service
  - Added proper variable initialization before try block in `async_force_update` service
  - Prevents secondary exceptions when logging errors if the initial `device_id` extraction fails

#### API Session Race Condition (Medium Severity)
- **Fixed**: Race condition in HTTP session creation
  - Added `asyncio.Lock()` with double-checked locking pattern to `_get_session()` method
  - Prevents multiple session instances from being created when called concurrently
  - Eliminates potential resource leaks and connection pool exhaustion

### Technical Details
- Modified Files:
  - `custom_components/loca/sensor.py` - Fixed availability property logic
  - `custom_components/loca/services.py` - Added variable pre-initialization
  - `custom_components/loca/api.py` - Added session lock for thread safety
- All 152 tests pass
- Full mypy type checking compliance

---

## [1.1.1-alpha.1] - 2025-09-18

### 🚨 Critical Bug Fixes

This alpha release addresses critical authentication and entity registration issues that broke the integration in v1.1.0.

#### Fixed
- **HTTPStatus import conflict**: Resolved `NameError: name 'HTTPStatus' is not defined` that prevented API authentication
- **Coordinator attribute error**: Resolved `AttributeError: 'LocaDataUpdateCoordinator' object has no attribute 'last_update_success_time'` that prevented entity registration
- Import resolution: Removed conflicting `http.HTTPStatus` import and properly used the local `HTTPStatus` class from constants
- Cache management: Updated entity data caching to use object identity tracking instead of timestamp-based invalidation
- Code quality: Fixed 44 linting issues and maintained full type safety with mypy

#### Technical Improvements
- **Linting**: All ruff checks now pass (fixed unused imports, style issues)
- **Type Safety**: Full mypy compliance across all 25 source files
- **Import Optimization**: Cleaned up unused imports across the codebase
- Improved error handling in the base entity mixin
- Better cache invalidation logic for entity data
- More robust coordinator integration

#### Testing
- ✅ All 29 API tests pass
- ✅ All 29 sensor tests pass
- ✅ All integration tests pass
- ✅ Full type checking compliance
- ✅ Zero linting issues

### Migration from v1.1.0
If you experienced authentication failures with v1.1.0:
1. Update to v1.1.1-alpha.1
2. Restart Home Assistant
3. The integration should authenticate successfully
4. All entities should be created properly

**Status**: Alpha Release - Use with caution

---

## [1.0.3] - 2024-XX-XX

### 🔒 Security Fixes

#### High Severity
- **Fixed GPS coordinate exposure in diagnostics**
  - GPS coordinates (latitude/longitude) are now properly redacted in diagnostic outputs
  - Address fields are also redacted to prevent location disclosure
  - Added `has_gps_data` boolean flag to indicate GPS availability without exposing coordinates
  - This prevents potential privacy breaches when users share diagnostic files for support

#### Medium Severity
- **Fixed partial API key disclosure**
  - Unique IDs now use SHA256 hash instead of raw API key characters
  - Removed API key and username length information from diagnostics
  - This prevents potential credential attacks from partial key exposure

### Changed
- Modified Files:
  - `custom_components/loca/diagnostics.py` - Redact sensitive location data
  - `custom_components/loca/config_flow.py` - Use hash for unique ID generation
  - `tests/test_diagnostics.py` - Update tests for redacted data
  - `tests/test_config_flow.py` - Update tests for new unique ID format

**Recommendation**: Users are strongly encouraged to update to this version to protect their location privacy and credential security.

---

## [1.0.2] - 2024-XX-XX

### 🐛 Critical Bug Fixes

#### Security & Stability Improvements
- **Fixed**: Removed unsafe cookie jar configuration that could pose security risks
- **Fixed**: Memory leak risk in API client session handling
- **Fixed**: Race condition in service registration that could cause duplicate service registration
- **Fixed**: Race condition in entity management during concurrent operations

#### Data Integrity Fixes
- **Fixed**: Inconsistent timezone handling causing datetime comparison issues
- **Fixed**: Potential division by zero in sensor time parsing that could cause crashes
- **Fixed**: Missing null checks for datetime objects preventing proper error handling
- **Fixed**: Config flow unique ID collision when using multiple accounts with same username

#### Code Quality Improvements
- **Fixed**: Direct access to private API authentication state
- **Removed**: Unused `parse_device_data` method reducing code complexity

### Technical Improvements
- API Client Updates:
  - Improved session management to prevent memory leaks
  - Added public `is_authenticated` property for proper state access
  - Ensured consistent UTC timezone usage across all datetime operations
  - Removed unsafe cookie jar configuration
- Entity Management:
  - Added documentation for Home Assistant's dynamic entity limitations
  - Improved null safety checks for datetime objects
  - Added safe division guards in time parsing logic
- Configuration Flow:
  - Improved unique ID generation using username + API key prefix
  - Better support for multiple Loca accounts on same Home Assistant instance

---

## [1.0.1] - 2024-XX-XX

### Fixed
- **Home Assistant aiohttp Session Warning**: Integration was creating and closing its own aiohttp session, triggering Home Assistant warnings about closing the shared session
  - Updated to properly use Home Assistant's shared aiohttp session via `aiohttp_client`
  - Eliminates warning messages in logs and ensures proper resource management

### Technical Improvements
- Modified `LocaAPI` class to accept `HomeAssistant` instance for proper session management
- Session is now obtained from `aiohttp_client.async_get_clientsession(hass)`
- Session cleanup only occurs in standalone/testing scenarios (when `hass` is None)
- `DataUpdateCoordinator` now passes `hass` instance to `LocaAPI`
- `ConfigFlow` properly initializes API client with `hass` reference
- Maintains backward compatibility for testing scenarios

---

## [1.0.0] - 2024-XX-XX

### Added - Initial Release 🎉

#### Core Functionality
- **Real-time GPS Tracking** - Monitor device locations with automatic updates
- **Battery Monitoring** - Track battery levels of your Loca devices
- **Multiple Sensor Types**:
  - Battery level sensor
  - Last seen timestamp
  - GPS accuracy indicator
- **Automatic Device Discovery** - Seamlessly detects all devices in your Loca account
- **Multi-device Support** - Track unlimited Loca devices simultaneously

#### Advanced Features
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

#### Provided Entities
For each Loca device, the following entities are created:
- `device_tracker.<device_name>` - Primary tracking entity
- `sensor.<device_name>_battery` - Battery level (%)
- `sensor.<device_name>_last_seen` - Last update timestamp
- `sensor.<device_name>_location_accuracy` - GPS accuracy (meters)

#### Requirements
- Home Assistant 2024.1.0 or newer
- Loca API credentials:
  - API key
  - Username
  - Password
- Active Loca device subscription

#### Known Issues
- Test cleanup may show warnings (framework issue, not affecting functionality)
- Some devices may show "Unknown" for certain attributes if not supported by the device

---

## Links

- [GitHub Repository](https://github.com/steynovich/ha-loca)
- [Issue Tracker](https://github.com/steynovich/ha-loca/issues)
- [Home Assistant Community](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration for Loca devices. It is not affiliated with or endorsed by Loca BV.