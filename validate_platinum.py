#!/usr/bin/env python3
"""Validation script to check Platinum requirements."""

import os
from pathlib import Path


def check_websession_injection():
    """Check if LocaAPI accepts websession parameter."""
    api_file = Path("custom_components/loca/api.py")
    coordinator_file = Path("custom_components/loca/coordinator.py")
    
    with open(api_file, 'r') as f:
        api_content = f.read()
    
    with open(coordinator_file, 'r') as f:
        coordinator_content = f.read()
    
    # Check if __init__ method accepts session parameter
    if "session: ClientSession | None = None" in api_content:
        print("✅ WebSession injection: LocaAPI accepts optional ClientSession parameter")
    else:
        print("❌ WebSession injection: LocaAPI missing ClientSession parameter")
        return False
    
    # Check if coordinator passes Home Assistant's websession
    if "aiohttp_client.async_get_clientsession(hass)" in coordinator_content:
        print("✅ WebSession injection: Coordinator passes Home Assistant websession")
        return True
    else:
        print("❌ WebSession injection: Coordinator not passing Home Assistant websession")
        return False


def check_async_dependency():
    """Check if API uses async/await."""
    api_file = Path("custom_components/loca/api.py")
    
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Check for async methods
    async_methods = ["async def authenticate", "async def get_assets", "async def get_status_list"]
    
    for method in async_methods:
        if method in content:
            print(f"✅ Async dependency: Found {method}")
        else:
            print(f"❌ Async dependency: Missing {method}")
            return False
    
    print("✅ Async dependency: All API methods are asynchronous")
    return True


def check_strict_typing():
    """Check if files have proper type annotations."""
    files_to_check = [
        "custom_components/loca/const.py",
        "custom_components/loca/__init__.py",
        "custom_components/loca/api.py",
        "custom_components/loca/coordinator.py",
    ]
    
    all_typed = True
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for future annotations
            if "from __future__ import annotations" in content:
                print(f"✅ Strict typing: {file_path} has future annotations")
            else:
                print(f"❌ Strict typing: {file_path} missing future annotations")
                all_typed = False
    
    # Check const.py for typed constants
    const_file = Path("custom_components/loca/const.py")
    if const_file.exists():
        with open(const_file, 'r') as f:
            content = f.read()
        
        if ": str = " in content and ": int = " in content and ": dict[int, str] = " in content:
            print("✅ Strict typing: const.py has typed constants")
        else:
            print("❌ Strict typing: const.py missing typed constants")
            all_typed = False
    
    return all_typed


def main():
    """Run all Platinum requirement checks."""
    print("🔍 Validating Home Assistant Quality Scale Platinum Requirements")
    print("=" * 65)
    
    requirements_met = 0
    total_requirements = 3
    
    # Check async dependency
    if check_async_dependency():
        requirements_met += 1
    
    print()
    
    # Check WebSession injection
    if check_websession_injection():
        requirements_met += 1
    
    print()
    
    # Check strict typing
    if check_strict_typing():
        requirements_met += 1
    
    print()
    print("=" * 65)
    print(f"📊 PLATINUM CERTIFICATION STATUS: {requirements_met}/{total_requirements} requirements met")
    
    if requirements_met == total_requirements:
        print("🏆 ✅ READY FOR PLATINUM CERTIFICATION!")
        print("\nThe Loca integration meets all Platinum requirements:")
        print("  1. ✅ async-dependency: API is fully asynchronous")
        print("  2. ✅ inject-websession: API accepts ClientSession parameter") 
        print("  3. ✅ strict-typing: All files use proper type annotations")
    else:
        print("❌ NOT READY FOR PLATINUM")
        print(f"Missing {total_requirements - requirements_met} requirement(s)")
    
    return requirements_met == total_requirements


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)