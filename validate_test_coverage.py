#!/usr/bin/env python3
"""Validation script to check comprehensive test coverage."""

from pathlib import Path


def analyze_test_coverage():
    """Analyze test coverage completeness."""
    print("🔍 Analyzing Test Coverage for Loca Integration")
    print("=" * 60)
    
    # Source files that should have tests
    source_files = {
        "__init__.py": "Integration lifecycle and setup",
        "api.py": "API client functionality", 
        "config_flow.py": "Configuration flow",
        "coordinator.py": "Data coordination",
        "device_tracker.py": "Device tracking",
        "sensor.py": "Sensor entities",
        "diagnostics.py": "Diagnostics functionality",
        "repairs.py": "Repair issues handling", 
        "services.py": "Service actions"
    }
    
    # Test files that exist
    test_files = {}
    tests_dir = Path("tests")
    if tests_dir.exists():
        for test_file in tests_dir.glob("test_*.py"):
            component = test_file.name.replace("test_", "").replace(".py", "")
            test_files[f"{component}.py"] = test_file
    
    print("📊 Component Test Coverage:")
    print("-" * 40)
    
    coverage_score = 0
    total_components = len(source_files)
    
    for source_file, description in source_files.items():
        if source_file in test_files:
            print(f"✅ {source_file:<20} - {description}")
            coverage_score += 1
        else:
            print(f"❌ {source_file:<20} - {description} (NO TESTS)")
    
    print()
    print("📈 Test File Statistics:")
    print("-" * 30)
    
    total_test_lines = 0
    for test_file_path in test_files.values():
        if test_file_path.exists():
            lines = len(test_file_path.read_text().splitlines())
            total_test_lines += lines
            print(f"   {test_file_path.name:<25} {lines:>4} lines")
    
    print(f"\n📋 Total test code: {total_test_lines} lines")
    
    # Recent feature coverage check
    print("\n🆕 Recent Feature Test Coverage:")
    print("-" * 35)
    
    recent_features = [
        ("WebSession injection", "test_api.py", ["test_init_with_session", "test_get_session_uses_external_session"]),
        ("Groups API", "test_api.py", ["test_get_groups_success", "test_update_groups_cache", "test_get_group_name"]),
        ("Dynamic icons", "test_sensor.py", ["test_icon_property_asset_info_sensor", "TestDynamicIconMapping"]),
        ("Diagnostics", "test_diagnostics.py", ["test_config_entry_diagnostics", "test_device_diagnostics"]), 
        ("Repairs", "test_repairs.py", ["TestRepairFlows", "TestIssueCreation"]),
        ("Services", "test_services.py", ["test_refresh_devices", "test_locate_device"])
    ]
    
    feature_coverage = 0
    for feature_name, test_file, test_methods in recent_features:
        test_file_path = Path("tests") / test_file
        if test_file_path.exists():
            content = test_file_path.read_text()
            methods_found = sum(1 for method in test_methods if method in content)
            if methods_found > 0:
                print(f"✅ {feature_name:<25} - {methods_found}/{len(test_methods)} tests")
                feature_coverage += 1
            else:
                print(f"❌ {feature_name:<25} - No tests found")
        else:
            print(f"❌ {feature_name:<25} - Test file missing")
    
    # Calculate coverage percentages
    component_coverage_pct = (coverage_score / total_components) * 100
    feature_coverage_pct = (feature_coverage / len(recent_features)) * 100
    
    print("\n" + "=" * 60)
    print("📊 COVERAGE SUMMARY")
    print("=" * 60)
    print(f"Component Coverage: {coverage_score}/{total_components} ({component_coverage_pct:.1f}%)")
    print(f"Recent Features:    {feature_coverage}/{len(recent_features)} ({feature_coverage_pct:.1f}%)")
    print(f"Total Test Lines:   {total_test_lines}")
    
    overall_score = (component_coverage_pct + feature_coverage_pct) / 2
    
    if overall_score >= 95:
        print("🏆 ✅ EXCELLENT TEST COVERAGE!")
        print("   Ready for production deployment")
    elif overall_score >= 85:
        print("✅ GOOD TEST COVERAGE")
        print("   Suitable for production use")
    elif overall_score >= 70:
        print("⚠️  ADEQUATE TEST COVERAGE")
        print("   Consider adding more tests for edge cases")
    else:
        print("❌ INSUFFICIENT TEST COVERAGE")
        print("   Additional tests needed before production")
    
    print(f"\nOverall Score: {overall_score:.1f}%")
    
    # Quality indicators
    print("\n🔍 Quality Indicators:")
    if total_test_lines > 1500:
        print("✅ Comprehensive test suite (>1500 lines)")
    elif total_test_lines > 1000:
        print("✅ Good test coverage (>1000 lines)")
    else:
        print("⚠️  Limited test coverage (<1000 lines)")
    
    return overall_score >= 85


if __name__ == "__main__":
    success = analyze_test_coverage()
    exit(0 if success else 1)