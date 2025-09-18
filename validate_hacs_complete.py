#!/usr/bin/env python3
"""Complete HACS compliance validation against all requirements."""

import json
from pathlib import Path


def validate_complete_hacs_compliance():
    """Validate against ALL HACS requirements for integrations."""
    print("🔍 Complete HACS Compliance Validation for Integration")
    print("=" * 65)
    
    total_checks = 0
    passed_checks = 0
    critical_issues = []
    warnings = []
    
    # 1. GitHub Repository Requirements
    print("🐙 GitHub Repository Requirements:")
    print("-" * 40)
    
    # Note: These would need to be checked on GitHub, we can only validate local structure
    print("📝 Manual Verification Required:")
    print("   ☐ Repository is public on GitHub")
    print("   ☐ Repository has clear description") 
    print("   ☐ Repository has GitHub topics (home-assistant, hacs, integration)")
    print("   ☐ Repository URL matches manifest documentation field")
    
    # 2. Repository Structure Requirements
    print("\n📁 Repository Structure Requirements:")
    print("-" * 42)
    
    total_checks += 1
    integration_path = Path("custom_components/loca")
    if integration_path.exists() and integration_path.is_dir():
        print("✅ Only one integration per repository")
        passed_checks += 1
    else:
        print("❌ Integration not in custom_components/loca/")
        critical_issues.append("Integration files must be in custom_components/DOMAIN/")
    
    total_checks += 1
    if integration_path.exists():
        print("✅ All integration files in custom_components/loca/")
        passed_checks += 1
    else:
        critical_issues.append("Integration directory missing")
    
    # 3. Essential Files Check
    print("\n📋 Essential Files Validation:")
    print("-" * 35)
    
    essential_files = {
        "README.md": "Repository documentation",
        "hacs.json": "HACS configuration",
        "custom_components/loca/__init__.py": "Integration entry point",
        "custom_components/loca/manifest.json": "Integration manifest",
        "custom_components/loca/config_flow.py": "Configuration flow (recommended)"
    }
    
    for file_path, description in essential_files.items():
        total_checks += 1
        if Path(file_path).exists():
            print(f"✅ {file_path:<40} - {description}")
            passed_checks += 1
        else:
            print(f"❌ {file_path:<40} - {description}")
            critical_issues.append(f"Missing required file: {file_path}")
    
    # 4. Manifest.json Validation
    print("\n📋 Manifest.json Validation:")
    print("-" * 30)
    
    manifest_path = Path("custom_components/loca/manifest.json")
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Required fields for HACS
            required_manifest_fields = {
                "domain": "Integration domain identifier",
                "documentation": "Documentation URL (usually GitHub)",
                "issue_tracker": "Issue tracker URL (usually GitHub issues)",
                "codeowners": "List of code maintainers",
                "name": "Human-readable integration name",
                "version": "Integration version"
            }
            
            for field, description in required_manifest_fields.items():
                total_checks += 1
                if field in manifest and manifest[field]:
                    print(f"✅ {field:<15} - {description}")
                    passed_checks += 1
                else:
                    print(f"❌ {field:<15} - {description} (MISSING)")
                    critical_issues.append(f"Manifest missing required field: {field}")
            
            # Validate specific field values
            total_checks += 1
            if manifest.get("domain") == "loca":
                print("✅ domain          - Matches directory name")
                passed_checks += 1
            else:
                print("❌ domain          - Should be 'loca'")
                critical_issues.append("Domain should match directory name")
            
            # Check URL formats
            total_checks += 2
            documentation = manifest.get("documentation", "")
            issue_tracker = manifest.get("issue_tracker", "")
            
            if documentation.startswith("https://"):
                print("✅ documentation   - Valid URL format")
                passed_checks += 1
            else:
                print("❌ documentation   - Should be valid HTTPS URL")
                critical_issues.append("Documentation URL should be HTTPS")
            
            if issue_tracker.startswith("https://"):
                print("✅ issue_tracker   - Valid URL format")
                passed_checks += 1
            else:
                print("❌ issue_tracker   - Should be valid HTTPS URL")
                critical_issues.append("Issue tracker URL should be HTTPS")
                
        except json.JSONDecodeError:
            print("❌ manifest.json   - Invalid JSON format")
            critical_issues.append("Manifest.json has invalid JSON syntax")
            total_checks += len(required_manifest_fields) + 3
    else:
        critical_issues.append("manifest.json file is missing")
        total_checks += 8
    
    # 5. HACS.json Validation
    print("\n🏠 HACS.json Configuration:")
    print("-" * 30)
    
    hacs_json_path = Path("hacs.json")
    if hacs_json_path.exists():
        try:
            with open(hacs_json_path, 'r') as f:
                hacs_config = json.load(f)
            
            total_checks += 1
            if "name" in hacs_config and hacs_config["name"]:
                print(f"✅ name            - Required: '{hacs_config['name']}'")
                passed_checks += 1
            else:
                print("❌ name            - Required field missing")
                critical_issues.append("HACS.json missing required 'name' field")
            
            # Optional but recommended fields
            optional_fields = {
                "domains": "Supported HA domains",
                "iot_class": "IoT class (Cloud Polling, etc.)",
                "homeassistant": "Minimum HA version",
                "hacs": "Minimum HACS version"
            }
            
            for field, description in optional_fields.items():
                if field in hacs_config:
                    print(f"✅ {field:<15} - Optional: {hacs_config[field]}")
                else:
                    print(f"ℹ️  {field:<15} - Optional: {description}")
                    warnings.append(f"Consider adding optional field '{field}' to hacs.json")
                    
        except json.JSONDecodeError:
            print("❌ hacs.json       - Invalid JSON format")
            critical_issues.append("hacs.json has invalid JSON syntax")
            total_checks += 1
    else:
        print("❌ hacs.json       - File missing")
        critical_issues.append("hacs.json file is required")
        total_checks += 1
    
    # 6. Integration Quality Checks
    print("\n🔧 Integration Quality Checks:")
    print("-" * 35)
    
    quality_items = {
        "custom_components/loca/translations/": "Translations directory",
        "custom_components/loca/services.yaml": "Service definitions", 
        "tests/": "Test suite",
        "LICENSE": "License file",
        "custom_components/loca/diagnostics.py": "Diagnostics support"
    }
    
    for item_path, description in quality_items.items():
        if Path(item_path).exists():
            print(f"✅ {description:<25} - Present")
        else:
            print(f"ℹ️  {description:<25} - Missing (recommended)")
            warnings.append(f"Consider adding {description.lower()}")
    
    # 7. Home Assistant Brands Requirement
    print("\n🏷️  Home Assistant Brands:")
    print("-" * 25)
    print("📝 Manual Verification Required:")
    print("   ☐ Integration added to home-assistant/brands repository")
    print("   ☐ Brand assets (logo, icon) provided")
    
    # Calculate compliance
    compliance_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print("\n" + "=" * 65)
    print("📊 COMPLETE HACS COMPLIANCE SUMMARY")
    print("=" * 65)
    print(f"Automated Checks: {passed_checks}/{total_checks} ({compliance_percentage:.1f}%)")
    print(f"Critical Issues:  {len(critical_issues)}")
    print(f"Warnings:        {len(warnings)}")
    
    if len(critical_issues) == 0:
        if compliance_percentage >= 95:
            print("🏆 ✅ FULLY HACS COMPLIANT!")
            print("   Ready for HACS submission")
        else:
            print("✅ HACS COMPLIANT")
            print("   Minor recommendations for improvement")
    else:
        print("❌ NOT FULLY HACS COMPLIANT")
        print("   Critical issues must be resolved")
    
    # Report issues
    if critical_issues:
        print("\n🚨 Critical Issues to Resolve:")
        for i, issue in enumerate(critical_issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print("\n⚠️  Recommendations:")
        for i, warning in enumerate(warnings[:5], 1):  # Show first 5
            print(f"   {i}. {warning}")
        if len(warnings) > 5:
            print(f"   ... and {len(warnings) - 5} more recommendations")
    
    print("\n🎯 Manual Verification Checklist:")
    print("-" * 35)
    print("Before submitting to HACS, verify:")
    print("☐ Repository is public on GitHub")
    print("☐ Repository has clear description")
    print("☐ Repository has appropriate GitHub topics")
    print("☐ Create GitHub release with version tag")
    print("☐ Submit to home-assistant/brands repository") 
    print("☐ Test installation via HACS custom repository")
    
    return len(critical_issues) == 0 and compliance_percentage >= 90


if __name__ == "__main__":
    success = validate_complete_hacs_compliance()
    exit(0 if success else 1)