# Release Notes - v1.0.3

## Security Update

This release addresses important security vulnerabilities discovered during a security audit.

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

### 🔧 Technical Changes

**Modified Files:**
- `custom_components/loca/diagnostics.py` - Redact sensitive location data
- `custom_components/loca/config_flow.py` - Use hash for unique ID generation
- `tests/test_diagnostics.py` - Update tests for redacted data
- `tests/test_config_flow.py` - Update tests for new unique ID format

### 📋 Testing

All existing tests have been updated and are passing:
- Configuration flow tests updated for new unique ID format
- Diagnostic tests updated to verify proper data redaction
- Full test suite passes with 100% compatibility

### 🔄 Compatibility

This update is fully backward compatible. No configuration changes are required.

### 📝 Recommendations

Users are strongly encouraged to update to this version to protect their location privacy and credential security.

---

**Full Changelog:** [v1.0.2...v1.0.3](https://github.com/steynovich/ha-loca/compare/v1.0.2...v1.0.3)