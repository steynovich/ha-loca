# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **ha-loca**, a production-ready Home Assistant custom integration for tracking Loca GPS devices. It provides comprehensive device tracking, sensor data, services, diagnostics, and repairs for Loca-branded GPS trackers through their cloud API.

**Current Version**: 1.1.5
**Integration Type**: Cloud polling hub integration
**HACS Compatible**: Yes (custom repository)

## Architecture

### Core Components

The integration follows Home Assistant's standard architecture patterns:

1. **API Client** (`api.py`)
   - Asynchronous HTTP client using aiohttp
   - Session-based authentication with API key + username/password
   - Endpoints: Login.json, Assets.json
   - Automatic session management and token refresh
   - Comprehensive error handling with custom exception types

2. **Data Coordinator** (`coordinator.py`)
   - Extends `DataUpdateCoordinator` for efficient polling
   - Default 60-second update interval
   - Tracks device status changes and empty device lists
   - Automatic repair issue creation for persistent problems

3. **Configuration Flow** (`config_flow.py`)
   - User-friendly setup wizard with validation
   - Reconfiguration support
   - Reauthentication flow for credential updates
   - Input validation using `validation.py`

4. **Platforms**:
   - `device_tracker.py` - GPS location tracking with zone support
   - `sensor.py` - 7 sensor types (battery, speed, location, accuracy, last_seen, asset_info, location_update)

5. **Services** (`services.py`)
   - `loca.refresh_devices` - Manual data refresh for all or specific config entries
   - `loca.force_update` - Force update for specific device by ID

6. **Supporting Modules**:
   - `diagnostics.py` - Privacy-aware diagnostic data collection
   - `repairs.py` - Automatic issue detection and repair suggestions
   - `validation.py` - Input validation and sanitization
   - `error_handling.py` - Custom exceptions and error decorators
   - `types.py` - TypedDict definitions for API responses
   - `base.py` - Base entity classes with common functionality
   - `const.py` - Constants, mappings, and configuration

### Entity Structure

**Base Entity** (`LocaBaseEntity`):
- Common device info, coordinator integration
- Attribute validation with fallbacks
- Automatic device name generation
- Unified error handling

**Device Tracker**:
- GPS coordinates with latitude/longitude
- Zone detection (home/not_home)
- Battery level as diagnostic attribute
- Speed and accuracy attributes

**Sensors**:
- Battery (diagnostic) - percentage with device class
- Speed - km/h with speed device class
- Location - human-readable address
- Accuracy (diagnostic, disabled by default) - GPS accuracy in meters
- Last Seen (diagnostic) - timestamp device class
- Asset Info (diagnostic) - brand/model/type information
- Location Update (diagnostic) - configuration status

## File Structure

```
ha-loca/
├── custom_components/loca/    # Main integration code
│   ├── __init__.py            # Integration setup/teardown
│   ├── api.py                 # LocaAPI client (317 lines)
│   ├── base.py                # Base entity classes (78 lines)
│   ├── config_flow.py         # Configuration flow (253 lines)
│   ├── const.py               # Constants and mappings (147 lines)
│   ├── coordinator.py         # Data update coordinator (133 lines)
│   ├── device_tracker.py      # GPS device tracker platform (102 lines)
│   ├── diagnostics.py         # Diagnostics support (116 lines)
│   ├── error_handling.py      # Error handling utilities (116 lines)
│   ├── repairs.py             # Repair issue management (76 lines)
│   ├── sensor.py              # Sensor platform - 7 types (288 lines)
│   ├── services.py            # Service implementations (113 lines)
│   ├── types.py               # Type definitions (48 lines)
│   ├── validation.py          # Input validation (95 lines)
│   ├── manifest.json          # Integration metadata
│   ├── services.yaml          # Service definitions
│   └── translations/          # Multi-language support (9 languages)
│       ├── en.json            # English (primary)
│       ├── nl.json            # Dutch
│       ├── de.json, es.json, fr.json, it.json, pl.json, pt.json, sv.json
├── tests/                     # Comprehensive test suite
│   ├── conftest.py            # Pytest fixtures and mocks
│   ├── test_api.py            # API client tests
│   ├── test_config_flow.py    # Config flow tests
│   ├── test_coordinator.py    # Coordinator tests
│   ├── test_device_tracker.py # Device tracker tests
│   ├── test_diagnostics.py    # Diagnostics tests
│   ├── test_init.py           # Integration setup tests
│   ├── test_repairs.py        # Repairs tests
│   ├── test_sensor.py         # Sensor platform tests
│   ├── test_services.py       # Services tests
│   ├── test_validation.py     # Validation tests
│   └── test_error_handling.py # Error handling tests
├── .github/workflows/         # CI/CD automation
│   ├── test.yml               # Pytest + coverage
│   ├── validate.yml           # HACS validation
│   ├── claude-pr-assistant.yml # Claude PR reviews
│   └── claude-code-review.yml  # Claude code reviews
├── assets/                    # Brand assets (icon.svg, logo.svg)
├── hacs.json                  # HACS configuration
├── requirements_test.txt      # Test dependencies
├── pytest.ini                 # Pytest configuration
└── validate_*.py              # HACS compliance scripts
```

## Development Setup

### Prerequisites
- Python 3.11+ (Home Assistant requirement)
- Home Assistant core development environment
- Loca API credentials (API key, username, password)

### Install Dependencies
```bash
# Test dependencies
pip install -r requirements_test.txt

# Includes: pytest, pytest-aiohttp, pytest-homeassistant-custom-component, aiohttp
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.loca --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Verbose output
pytest -v

# Run with Home Assistant test fixtures
pytest --homeassistant
```

### Code Quality Tools

The project uses standard Python tooling:

```bash
# Type checking (if mypy is configured)
mypy custom_components/loca

# Linting (if ruff/flake8 is configured)
ruff check custom_components/loca

# Formatting
black custom_components/loca
```

### Testing Strategy

**Unit Tests**:
- Mock API responses using `aiohttp` fixtures
- Test coordinator update logic
- Validate entity state calculations
- Test error handling paths

**Integration Tests**:
- Use Home Assistant test harness
- Test full setup/teardown flows
- Validate entity registration
- Test service calls end-to-end

**Mock Data**:
- Sample API responses in test fixtures
- Covers various device states (online, offline, low battery)
- Edge cases (empty device lists, malformed responses)

## API Integration

### Loca API Details
- **Base URL**: `https://api.loca.nl/v1/`
- **Authentication**: Session cookies after POST to Login.json
- **Response Format**: JSON with "user" object containing devices
- **Rate Limiting**: Recommended 60+ second intervals
- **Requirements**: API key + username + password

### API Client Design
- Uses `aiohttp.ClientSession` with connection pooling
- Automatic session refresh on 401 errors
- Timeout handling (default 30 seconds)
- Comprehensive logging with sensitive data sanitization
- Retry logic for transient failures

### Data Flow
1. User configures integration via UI
2. Config flow validates credentials with test login
3. Coordinator polls API every 60 seconds
4. API client fetches Assets.json with device data
5. Coordinator updates all entities with new data
6. Entities parse and validate attributes
7. Home Assistant updates UI with new states

## Security Considerations

### Implemented Security Features
✅ Credentials stored in Home Assistant's encrypted config storage
✅ Sensitive data sanitization in all log messages (`sanitize_for_logging()`)
✅ Diagnostics redact API keys, passwords, and GPS coordinates
✅ HTTPS enforced for all API communication
✅ Input validation on all user inputs (API key, username, password)
✅ Reauthentication flow requires password re-entry (not cached)
✅ No sensitive data in entity attributes exposed to UI
✅ Session cookies not persisted to disk

### Security Best Practices
- SSL certificate verification is enabled by default in aiohttp
- API tokens/cookies only stored in memory during runtime
- Device IDs are non-sensitive and safe to log
- GPS coordinates only exposed through entity states (standard HA pattern)

## Error Handling

### Exception Hierarchy
```python
HomeAssistantError
├── ConfigEntryAuthFailed      # Authentication failures → triggers reauth
├── LocaAPIUnavailableError    # API connectivity issues → retry
├── CannotConnect              # Network/DNS issues → setup fails
├── InvalidAuth                # Bad credentials → setup fails
└── ValidationError            # Invalid input → user feedback
```

### Error Handling Patterns
1. **API Errors**: `@handle_api_errors` decorator for consistent handling
2. **Validation Errors**: Explicit `ValidationError` with user-friendly messages
3. **Coordinator Errors**: Graceful degradation with `UpdateFailed` exceptions
4. **Entity Errors**: Fallback to None/Unknown with warning logs

### Repair System
- Automatically creates repair issues for persistent problems
- Tracks consecutive empty device list occurrences (threshold: 3)
- Provides actionable guidance for common issues
- Integrates with Home Assistant's repair UI

## Translation Support

**Supported Languages**: 9 languages (EN, NL, DE, ES, FR, IT, PL, PT, SV)

**Translation Keys**:
- Config flow UI strings
- Error messages
- Service descriptions
- Entity names and state labels

**Translation Files**: `translations/{lang}.json`

**Adding New Language**:
1. Copy `translations/en.json` to `translations/{lang}.json`
2. Translate all values (keep keys unchanged)
3. Test with Home Assistant language settings
4. Ensure special characters are properly escaped

## HACS Integration

### HACS Configuration
- **Type**: Custom integration
- **Installation**: Via custom repository URL
- **Validation**: GitHub Actions workflow validates HACS compliance
- **Releases**: Semantic versioning with zip archives

### HACS Requirements
✅ `hacs.json` present with correct schema
✅ `manifest.json` with required fields
✅ README.md with installation instructions
✅ Proper repository structure
✅ Release workflow creating zip assets
✅ GitHub topics: `home-assistant`, `hacs`, `integration`

## GitHub Actions Workflows

### CI/CD Pipeline
1. **test.yml** - Runs pytest suite on push/PR
2. **validate.yml** - HACS compliance checks
3. **claude-pr-assistant.yml** - Automated PR reviews by Claude
4. **claude-code-review.yml** - Code quality analysis by Claude

### Release Process
1. Update version in `manifest.json`
2. Create git tag: `git tag v1.x.x`
3. Push tag: `git push --tags`
4. GitHub Actions creates release with zip asset
5. HACS detects new release automatically

## Common Development Tasks

### Adding a New Sensor
1. Define sensor class in `sensor.py` extending `LocaSensorEntity`
2. Implement `native_value` property with validation
3. Set `_attr_device_class` and `_attr_state_class`
4. Add to `async_setup_entry()` sensor list
5. Add translations for entity name/states
6. Write unit tests in `tests/test_sensor.py`
7. Update README.md entity list

### Adding a New Service
1. Define service in `services.yaml` with schema
2. Implement handler in `services.py`
3. Register in `__init__.py` via `async_setup_services()`
4. Add translations for service name/description
5. Write tests in `tests/test_services.py`
6. Document in README.md

### Debugging Integration Issues
1. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.loca: debug
   ```
2. Check Home Assistant logs: Settings → System → Logs
3. Use diagnostics: Device → Download Diagnostics
4. Check repair issues: Settings → System → Repairs
5. Use `/api/states` to inspect entity states directly

## Known Limitations

1. **Polling Only**: No real-time push notifications (Loca API limitation)
2. **Update Interval**: Minimum recommended 30 seconds to avoid rate limiting
3. **GPS Accuracy**: Depends on device hardware and cellular signal
4. **Empty Device Lists**: API returns empty list for new/inactive accounts (this is expected)
5. **Session Management**: Sessions may expire, triggering reauthentication

## Contributing Guidelines

### Code Standards
- Follow Home Assistant style guide
- Use type hints for all function signatures
- Write docstrings for public classes/methods
- Keep line length under 88 characters (Black formatter)
- Use meaningful variable names

### Testing Requirements
- All new code must have unit tests
- Maintain >80% code coverage
- Test both success and error paths
- Mock external API calls
- Use Home Assistant test fixtures

### PR Process
1. Fork repository and create feature branch
2. Write code with tests
3. Run test suite locally: `pytest`
4. Update README.md if adding user-facing features
5. Update translations for all UI strings
6. Submit PR with clear description
7. Address Claude Code Review feedback

## Additional Resources

- **Home Assistant Dev Docs**: https://developers.home-assistant.io/
- **HACS Documentation**: https://hacs.xyz/docs/publish/start
- **Loca API Support**: Contact Loca support for API credentials
- **Issue Tracker**: https://github.com/steynovich/ha-loca/issues

## Version History

- **1.1.5** (Current) - Fixed AttributeError for last_update_success_time
- **1.1.4** - Entity initialization improvements
- **1.1.3** - Coordinator stability fixes
- **1.1.2** - Diagnostics privacy enhancements
- **1.1.1** - Authentication fixes
- **1.1.0** - Added repairs, diagnostics, services
- **1.0.x** - Initial release with basic tracking

## Notes for AI Assistants

When working with this codebase:
- This is a **production integration** - prioritize stability and backward compatibility
- Always validate changes against Home Assistant's integration quality checklist
- Test with real Loca API credentials when possible (or use comprehensive mocks)
- Security: Never log or expose API keys, passwords, or exact GPS coordinates
- Breaking changes require major version bump and migration logic
- UI strings must be translatable - never hardcode English text in Python
- Follow Home Assistant naming conventions for entities: `{platform}.{domain}_{device}_{sensor}`
