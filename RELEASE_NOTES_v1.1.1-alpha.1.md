# Release v1.1.1-alpha.1 - Critical Authentication Fixes

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