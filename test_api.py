#!/usr/bin/env python3
"""Simple test script to debug Loca API authentication issues."""

import asyncio
import aiohttp
import json
import sys
import os

# Add the custom_components path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.loca.api import LocaAPI
from custom_components.loca.const import API_BASE_URL, API_LOGIN_ENDPOINT

async def test_api_directly():
    """Test the API directly to diagnose issues."""
    print("=== Loca API Direct Test ===")
    
    # Get credentials from user
    api_key = input("Enter your API key: ").strip()
    username = input("Enter your username: ").strip()
    password = input("Enter your password: ").strip()
    
    if not all([api_key, username, password]):
        print("ERROR: All credentials are required!")
        return
    
    print("\nTesting with:")
    print(f"- API Key: {'*' * (len(api_key) - 4)}{api_key[-4:] if len(api_key) > 4 else '***'}")
    print(f"- Username: {username}")
    print(f"- Password: {'*' * len(password)}")
    print(f"- Endpoint: {API_BASE_URL}/{API_LOGIN_ENDPOINT}")
    
    # Test 1: Direct HTTP request
    print("\n=== Test 1: Direct HTTP Request ===")
    async with aiohttp.ClientSession() as session:
        login_data = {
            "key": api_key,
            "username": username,
            "password": password,
        }
        
        try:
            async with session.post(
                f"{API_BASE_URL}/{API_LOGIN_ENDPOINT}",
                json=login_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"HTTP Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                try:
                    response_text = await response.text()
                    print(f"Raw response: {response_text[:500]}")
                    
                    # Try to parse as JSON
                    if response_text:
                        try:
                            data = json.loads(response_text)
                            print(f"Parsed JSON: {json.dumps(data, indent=2)}")
                            
                            # Analyze the response structure
                            print("\nResponse Analysis:")
                            print(f"- Has 'status' field: {'status' in data}")
                            print(f"- Status value: {data.get('status', 'N/A')}")
                            print(f"- Has 'user' field: {'user' in data}")
                            print(f"- Has 'message' field: {'message' in data}")
                            print(f"- Has 'error' field: {'error' in data}")
                            print(f"- All keys: {list(data.keys())}")
                            
                            # Check if it's a successful login (has user object)
                            if data.get("user"):
                                print("✅ SUCCESS: Login appears successful")
                                user = data["user"]
                                print(f"- Username: {user.get('username')}")
                                print(f"- User ID: {user.get('userid')}")
                            else:
                                print("❌ FAILED: No user object in response")
                            
                        except json.JSONDecodeError as e:
                            print(f"JSON Parse Error: {e}")
                    else:
                        print("Empty response body")
                        
                except Exception as e:
                    print(f"Error reading response: {e}")
                    
        except Exception as e:
            print(f"Request failed: {e}")
    
    # Test 2: Using our LocaAPI class
    print("\n=== Test 2: Using LocaAPI Class ===")
    api = LocaAPI(api_key, username, password)
    try:
        success = await api.authenticate()
        print(f"Authentication result: {success}")
        
        if success:
            print("Testing asset retrieval...")
            assets = await api.get_assets()
            print(f"Assets retrieved: {len(assets) if assets else 0}")
            
            if assets:
                print("First asset preview:")
                print(json.dumps(assets[0], indent=2, default=str))
                
                # Test legacy device parsing (from Assets)
                print("\nTesting legacy device data parsing from Assets:")
                parsed = api.parse_device_data(assets[0])
                print("Parsed device data from Assets:")
                print(json.dumps(parsed, indent=2, default=str))
            
            print("\n" + "="*60)
            print("MAIN DATA SOURCE: StatusList.json (Real-time GPS Data)")
            print("="*60)
            
            print("Testing Groups retrieval...")
            await api.update_groups_cache()
            groups = await api.get_groups()
            print(f"Groups retrieved: {len(groups) if groups else 0}")
            
            if groups:
                print("Available groups:")
                for group in groups:
                    print(f"  - ID {group.get('id')}: {group.get('label')}")
            
            print("\nTesting StatusList retrieval...")
            status_list = await api.get_status_list()
            print(f"StatusList entries retrieved: {len(status_list) if status_list else 0}")
            
            if status_list:
                print("\nFirst status entry raw data:")
                print(json.dumps(status_list[0], indent=2, default=str))
                
                # Test status parsing as device (this is the main data now)
                print("\nTesting status parsing as device (NEW METHOD):")
                parsed_device = api.parse_status_as_device(status_list[0])
                print("Parsed status as device:")
                print(json.dumps(parsed_device, indent=2, default=str))
                
                print(f"\n🗺️  GPS Coordinates: {parsed_device['latitude']}, {parsed_device['longitude']}")
                print(f"📍 Address: {parsed_device.get('address', 'Unknown')}")
                print(f"📊 GPS Accuracy (HDOP): {parsed_device['gps_accuracy']}")
                print(f"🏷️  Device Name: {parsed_device['name']}")
                print(f"🆔 Device ID: {parsed_device['device_id']}")
                
                print("\n--- SENSOR DATA PREVIEW ---")
                
                # Battery Sensor
                battery = parsed_device['battery_level']
                print(f"🔋 Battery Sensor: {battery}% (sensor.{parsed_device['name'].lower()}_battery)")
                
                # Speed Sensor  
                speed = parsed_device['speed']
                print(f"⚡ Speed Sensor: {speed} km/h (sensor.{parsed_device['name'].lower()}_speed)")
                print(f"   └─ Attributes: GPS={parsed_device['gps_accuracy']}m accuracy, {parsed_device['satellites']} satellites")
                
                # Location Sensor (diagnostic)
                address = parsed_device.get('address', 'Unknown')
                print(f"📍 Location Sensor: {address} (Dutch format)")
                address_details = parsed_device.get('address_details', {})
                if address_details:
                    components = [f"{k}: {v}" for k, v in address_details.items() if v]
                    if components:
                        print(f"   └─ Text components: {', '.join(components[:3])}{'...' if len(components) > 3 else ''}")
                    print("   └─ Format: Street Number, Zipcode City, Country")
                
                # Asset Info Sensor
                asset_info = parsed_device['asset_info']
                asset_display = f"{asset_info['brand']} {asset_info['model']}".strip() or "Unknown Asset"
                print(f"🚗 Asset Info Sensor: {asset_display}")
                group_info = f"Group: {asset_info['group_name']}" if asset_info['group_name'] else "No group"
                print(f"   └─ Serial: {asset_info['serial']}, Type: {asset_info['type']}, {group_info}")
                
                # Location Update Sensor
                location_update = parsed_device.get('location_update', {})
                if location_update:
                    always = location_update.get('always', 0)
                    update_status = "Always on" if always == 1 else "Scheduled"
                    print(f"🔄 Location Update Sensor: {update_status}")
                    
                    # Show detailed frequency info in attributes
                    frequency = location_update.get('frequency', 0)
                    timeofday = location_update.get('timeofday', 0)
                    if timeofday:
                        # Parse format: HHMM00 or similar (e.g., 91000 = 9:10)
                        if timeofday >= 1000:
                            # Extract hours and minutes from HHMM00 format
                            hours = timeofday // 10000
                            minutes = (timeofday % 10000) // 100
                            # Ensure valid time range
                            hours = min(23, max(0, hours))
                            minutes = min(59, max(0, minutes))
                            print(f"   └─ Attributes: Update time {hours:02d}:{minutes:02d}, Frequency: {frequency}s")
                        else:
                            # Fallback: treat as seconds since midnight
                            timeofday = timeofday % 86400
                            hours = timeofday // 3600
                            minutes = (timeofday % 3600) // 60
                            hours = min(23, max(0, hours))
                            minutes = min(59, max(0, minutes))
                            print(f"   └─ Attributes: Update time {hours:02d}:{minutes:02d}, Frequency: {frequency}s")
                    else:
                        print(f"   └─ Attributes: Frequency: {frequency}s")
                else:
                    print("🔄 Location Update Sensor: Not configured")
                
                # Last Seen Sensor
                last_seen = parsed_device.get('last_seen')
                if last_seen:
                    print(f"🕐 Last Seen Sensor: {last_seen.isoformat()}")
                    print(f"   └─ Source: {parsed_device.get('location_source', 'Unknown')}")
                else:
                    print("🕐 Last Seen Sensor: No timestamp available")
                
                # Location Accuracy Sensor (diagnostic, disabled by default)
                print(f"📊 Location Accuracy Sensor: {parsed_device['gps_accuracy']}m (diagnostic, disabled by default)")
                
                print(f"\n📶 Additional Info: GSM signal strength {parsed_device['signal_strength']}")
                if location_label := parsed_device.get('location_label'):
                    print(f"📍 Named Location: {location_label}")
                
                # Test all status entries
                print(f"\n{'='*60}")
                print(f"ALL DEVICES SUMMARY ({len(status_list)} devices)")
                print(f"{'='*60}")
                
                for i, status_entry in enumerate(status_list):
                    parsed = api.parse_status_as_device(status_entry)
                    battery_info = f"{parsed['battery_level']}%" if parsed['battery_level'] is not None else "N/A"
                    asset_info = parsed['asset_info']
                    vehicle = f"{asset_info['brand']} {asset_info['model']}".strip() or "Unknown Vehicle"
                    
                    print(f"🚗 Device {i+1}: {parsed['name']} (ID: {parsed['device_id']})")
                    print(f"   📍 Location: ({parsed['latitude']}, {parsed['longitude']})")
                    print(f"   🏠 Address: {parsed.get('address', 'No address')}")
                    print(f"   🔋 Battery: {battery_info} | ⚡ Speed: {parsed['speed']} km/h")
                    print(f"   🚙 Vehicle: {vehicle} | 📱 Serial: {asset_info['serial']}")
                    print(f"   🛰️  GPS: {parsed['satellites']} sats, {parsed['gps_accuracy']}m accuracy")
                    if location_label := parsed.get('location_label'):
                        print(f"   📍 Named Location: {location_label}")
                    print()
                    
                print(f"✅ SUCCESS: Found {len(status_list)} devices with real-time GPS data!")
                print("\n📊 HOME ASSISTANT ENTITIES THAT WILL BE CREATED:")
                print("For each device, the following entities will be available:")
                print("  📍 device_tracker.{device_name} - GPS location on map")
                print("  🔋 sensor.{device_name}_battery - Battery percentage")
                print("  ⚡ sensor.{device_name}_speed - Current speed (km/h)")
                print("  🚗 sensor.{device_name}_asset_information - Vehicle/asset details")
                print("  🕐 sensor.{device_name}_last_seen - Last update timestamp")
                print("  📍 sensor.{device_name}_location - Textual location info (diagnostic)")
                print("  🔄 sensor.{device_name}_location_update_config - Update settings (diagnostic)")
                print("  📊 sensor.{device_name}_location_accuracy - GPS accuracy (diagnostic, disabled)")
                print("\nThese devices will appear as device trackers in Home Assistant with live location updates.")
            else:
                print("⚠️  No devices found in StatusList - this means no GPS devices will be created!")
                print("Make sure your Loca account has active GPS devices.")
            
            print("\n" + "="*50)
            print("REFERENCE DATA: UserLocationList (Static Locations)")
            print("="*50)
            
            print("Testing user locations retrieval...")
            locations = await api.get_user_locations()
            print(f"User locations retrieved: {len(locations) if locations else 0}")
            
            if locations:
                print("Static locations in your account:")
                for i, location in enumerate(locations):
                    print(f"  {i+1}. {location.get('label', 'Unnamed')}: ({location.get('latitude')}, {location.get('longitude')})")
                print("\nNote: These are static locations/geofences, not real-time device positions.")
            else:
                print("No static locations configured.")
        
    except Exception as e:
        print(f"LocaAPI test failed: {e}")
    finally:
        await api.close()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_api_directly())