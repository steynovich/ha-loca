#!/usr/bin/env python3
"""Validation script to check HACS compliance requirements."""

import json
from pathlib import Path


def check_hacs_compliance():
    """Check HACS compliance requirements."""
    print("🔍 Validating HACS Compliance for Loca Integration")
    print("=" * 60)
    
    requirements_met = 0
    total_requirements = 0
    
    # Repository Structure Requirements
    print("📁 Repository Structure Requirements:")
    print("-" * 40)
    
    total_requirements += 3
    
    # Check 1: Integration files in correct directory
    integration_path = Path("custom_components/loca")
    if integration_path.exists() and integration_path.is_dir():
        print("✅ Integration files in custom_components/loca/ directory")
        requirements_met += 1
    else:
        print("❌ Integration files not in correct directory structure")
    
    # Check 2: README exists
    readme_path = Path("README.md")
    if readme_path.exists():
        print("✅ README.md file exists")
        requirements_met += 1
    else:
        print("❌ README.md file missing")
    
    # Check 3: hacs.json exists
    hacs_json_path = Path("hacs.json")
    if hacs_json_path.exists():
        print("✅ hacs.json file exists")
        requirements_met += 1
    else:
        print("❌ hacs.json file missing")
    
    print()
    
    # Manifest.json Requirements
    print("📋 Manifest.json Requirements:")
    print("-" * 35)
    
    manifest_path = Path("custom_components/loca/manifest.json")
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            required_keys = ["domain", "documentation", "issue_tracker", "codeowners", "name", "version"]
            
            for key in required_keys:
                total_requirements += 1
                if key in manifest:
                    print(f"✅ manifest.json has '{key}': {manifest[key]}")
                    requirements_met += 1
                else:
                    print(f"❌ manifest.json missing required key: '{key}'")
            
            # Check specific values
            if manifest.get("domain") == "loca":
                print("✅ Domain matches integration name")
            else:
                print("❌ Domain should match 'loca'")
                
        except json.JSONDecodeError:
            print("❌ manifest.json is not valid JSON")
            total_requirements += 6  # All required keys failed
    else:
        print("❌ manifest.json file missing")
        total_requirements += 6
    
    print()
    
    # HACS.json Requirements  
    print("🏠 HACS.json Configuration:")
    print("-" * 30)
    
    if hacs_json_path.exists():
        try:
            with open(hacs_json_path, 'r') as f:
                hacs_config = json.load(f)
            
            total_requirements += 1
            if "name" in hacs_config:
                print(f"✅ hacs.json has 'name': {hacs_config['name']}")
                requirements_met += 1
            else:
                print("❌ hacs.json missing required 'name' field")
            
            # Check optional but recommended fields
            optional_fields = {
                "domains": "Supported domains",
                "iot_class": "IoT class specification",
                "homeassistant": "Home Assistant version requirement"
            }
            
            for field, description in optional_fields.items():
                if field in hacs_config:
                    print(f"✅ hacs.json has '{field}': {hacs_config[field]} - {description}")
                else:
                    print(f"ℹ️  hacs.json missing optional '{field}' - {description}")
                    
        except json.JSONDecodeError:
            print("❌ hacs.json is not valid JSON")
            total_requirements += 1
    
    print()
    
    # File Structure Analysis
    print("📂 File Structure Analysis:")
    print("-" * 30)
    
    # Check for essential integration files
    essential_files = {
        "__init__.py": "Integration entry point",
        "manifest.json": "Integration manifest", 
        "config_flow.py": "Configuration flow",
        "api.py": "API client",
        "coordinator.py": "Data coordinator",
        "sensor.py": "Sensor platform",
        "device_tracker.py": "Device tracker platform"
    }
    
    integration_files_count = 0
    for filename, description in essential_files.items():
        filepath = integration_path / filename
        if filepath.exists():
            print(f"✅ {filename:<20} - {description}")
            integration_files_count += 1
        else:
            print(f"❌ {filename:<20} - {description} (MISSING)")
    
    print(f"\n📊 Integration files: {integration_files_count}/{len(essential_files)}")
    
    # Check for additional quality files
    print("\n🔧 Additional Quality Files:")
    print("-" * 30)
    
    quality_files = {
        "translations/en.json": "English translations",
        "translations/nl.json": "Dutch translations", 
        "services.yaml": "Service definitions",
        "diagnostics.py": "Diagnostics support",
        "repairs.py": "Repair issues support"
    }
    
    quality_files_count = 0
    for filename, description in quality_files.items():
        filepath = integration_path / filename
        if filepath.exists():
            print(f"✅ {filename:<25} - {description}")
            quality_files_count += 1
        else:
            print(f"❌ {filename:<25} - {description}")
    
    # Test coverage check
    tests_dir = Path("tests")
    if tests_dir.exists() and len(list(tests_dir.glob("test_*.py"))) > 0:
        test_count = len(list(tests_dir.glob("test_*.py")))
        print(f"✅ {'tests/':<25} - {test_count} test files")
        quality_files_count += 1
    else:
        print(f"❌ {'tests/':<25} - No test files found")
    
    # Calculate compliance score
    compliance_percentage = (requirements_met / total_requirements) * 100 if total_requirements > 0 else 0
    
    print("\n" + "=" * 60)
    print("📊 HACS COMPLIANCE SUMMARY")
    print("=" * 60)
    print(f"Required Features: {requirements_met}/{total_requirements} ({compliance_percentage:.1f}%)")
    print(f"Integration Files: {integration_files_count}/{len(essential_files)}")
    print(f"Quality Features:  {quality_files_count}/{len(quality_files) + 1}")  # +1 for tests
    
    if compliance_percentage >= 100:
        print("🏆 ✅ FULLY HACS COMPLIANT!")
        print("   Ready for HACS submission")
    elif compliance_percentage >= 90:
        print("✅ HACS COMPLIANT")
        print("   Minor improvements recommended")
    elif compliance_percentage >= 80:
        print("⚠️  MOSTLY HACS COMPLIANT")
        print("   Some requirements need attention")
    else:
        print("❌ NOT HACS COMPLIANT")
        print("   Multiple requirements need to be addressed")
    
    # Additional recommendations
    print("\n🎯 Recommendations for HACS:")
    print("-" * 30)
    
    if compliance_percentage >= 90:
        print("✅ Create GitHub release with version tag")
        print("✅ Submit to home-assistant/brands repository")
        print("✅ Ensure repository is public on GitHub")
        print("✅ Add GitHub topics for discoverability")
        print("✅ Consider adding 'my-link' for easy installation")
    
    return compliance_percentage >= 90


if __name__ == "__main__":
    success = check_hacs_compliance()
    exit(0 if success else 1)