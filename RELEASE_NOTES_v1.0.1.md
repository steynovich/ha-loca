# Release v1.0.1 - Bug Fix Release

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