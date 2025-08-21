# Release v1.0.0 - Initial Release

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