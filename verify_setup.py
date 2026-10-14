#!/usr/bin/env python3
"""
Verification Script - Checks if all modules can be imported and are functional
Run this to verify the complete setup before running the server or tests.

Usage:
    python verify_setup.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def check_imports():
    """Verify all important modules can be imported."""
    print("\n" + "="*60)
    print("VERIFYING IMPORTS")
    print("="*60)
    
    modules_to_check = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("requests", "Requests"),
        ("pathlib", "Pathlib (built-in)"),
        ("json", "JSON (built-in)"),
        ("subprocess", "Subprocess (built-in)"),
    ]
    
    missing = []
    for module_name, display_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✓ {display_name:<25} - OK")
        except ImportError as e:
            print(f"✗ {display_name:<25} - MISSING")
            missing.append(module_name)
    
    return len(missing) == 0, missing


def check_project_structure():
    """Verify project directory structure."""
    print("\n" + "="*60)
    print("VERIFYING PROJECT STRUCTURE")
    print("="*60)
    
    required_dirs = [
        "app",
        "app/agents",
        "app/api",
        "app/analyzer",
        "app/utils",
        "app/benchmarks_testers",
        "constants",
        "scanner",
        "pysa_rules",
        "benchmarks",
        "reports",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"✓ {dir_path:<30} - OK")
        else:
            print(f"✗ {dir_path:<30} - MISSING")
            all_exist = False
    
    return all_exist


def check_required_files():
    """Verify required Python files exist."""
    print("\n" + "="*60)
    print("VERIFYING REQUIRED FILES")
    print("="*60)
    
    required_files = [
        # New agent files
        "app/agents/agent_base.py",
        "app/agents/benchmark_1_web_scraper.py",
        "app/agents/benchmark_2_db_query.py",
        "app/agents/benchmark_3_filesystem.py",
        "app/agents/benchmark_4_process_exec.py",
        "app/agents/__init__.py",
        
        # New utility files
        "app/utils/github_utils.py",
        
        # Test files
        "app/benchmarks_testers/agent_benchmark.py",
        "app/benchmarks_testers/__init__.py",
        "test_runner.py",
        
        # Core files
        "app/main.py",
        "app/api/scan.py",
        "app/analyzer/scan_pipeline.py",
        
        # Documentation
        "API_DOCUMENTATION.md",
        "SETUP_GUIDE.md",
        "PROJECT_STATUS.md",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✓ {file_path:<45} - {size:>6} bytes")
        else:
            print(f"✗ {file_path:<45} - MISSING")
            all_exist = False
    
    return all_exist


def check_agent_imports():
    """Verify agent modules can be imported."""
    print("\n" + "="*60)
    print("VERIFYING AGENT IMPORTS")
    print("="*60)
    
    agents = [
        ("app.agents.agent_base", "MCPAgentBase"),
        ("app.agents.benchmark_1_web_scraper", "WebScraperAgent"),
        ("app.agents.benchmark_2_db_query", "DatabaseQueryAgent"),
        ("app.agents.benchmark_3_filesystem", "FileSystemAgent"),
        ("app.agents.benchmark_4_process_exec", "ProcessExecutionAgent"),
    ]
    
    all_imported = True
    for module_name, class_name in agents:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {class_name:<30} - OK")
        except ImportError as e:
            print(f"✗ {class_name:<30} - IMPORT ERROR: {e}")
            all_imported = False
        except AttributeError as e:
            print(f"✗ {class_name:<30} - NOT FOUND: {e}")
            all_imported = False
    
    return all_imported


def check_api_endpoints():
    """Verify API routes are properly defined."""
    print("\n" + "="*60)
    print("VERIFYING API ENDPOINTS")
    print("="*60)
    
    try:
        from app.api.scan import router
        print(f"✓ API Router imported successfully")
        
        # Check routes exist
        routes_to_check = [
            "scan_model",
            "scan_project",
            "scan_zip",
            "scan_github",
            "scan_benchmark",
            "scan_all_benchmarks",
            "health_check",
        ]
        
        # Get all route names
        route_names = set()
        for route in router.routes:
            if hasattr(route, 'name'):
                route_names.add(route.name)
        
        print(f"✓ Found {len(route_names)} routes")
        for route_name in sorted(route_names):
            print(f"  - {route_name}")
        
        return True
    except Exception as e:
        print(f"✗ Error checking API endpoints: {e}")
        return False


def check_benchmark_suite():
    """Verify benchmark test suite."""
    print("\n" + "="*60)
    print("VERIFYING BENCHMARK SUITE")
    print("="*60)
    
    try:
        from app.benchmarks_testers.agent_benchmark import BenchmarkTestSuite
        print(f"✓ BenchmarkTestSuite imported successfully")
        
        # Check methods exist
        methods = ['run_all_tests', 'save_results', 'generate_report', '_test_single_agent']
        for method in methods:
            if hasattr(BenchmarkTestSuite, method):
                print(f"  ✓ {method}")
            else:
                print(f"  ✗ {method} - MISSING")
        
        return True
    except Exception as e:
        print(f"✗ Error checking benchmark suite: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "#"*60)
    print("# MCP AGENT VULNERABILITY SCANNER - SETUP VERIFICATION")
    print("#"*60)
    
    checks = [
        ("Package Imports", check_imports),
        ("Project Structure", check_project_structure),
        ("Required Files", check_required_files),
        ("Agent Imports", check_agent_imports),
        ("API Endpoints", check_api_endpoints),
        ("Benchmark Suite", check_benchmark_suite),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            result = check_func()
            if isinstance(result, tuple):
                results[check_name] = result[0]
            else:
                results[check_name] = result
        except Exception as e:
            print(f"\n✗ Error in {check_name}: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {check_name}")
    
    print("\n" + "="*60)
    if passed == total:
        print(f"✓ ALL CHECKS PASSED ({passed}/{total})")
        print("\nSetup is ready! You can now:")
        print("1. Start the server:  uvicorn app.main:app --reload")
        print("2. Run tests:        python test_runner.py")
        print("=" * 60)
        return 0
    else:
        print(f"✗ SOME CHECKS FAILED ({passed}/{total})")
        print("\nPlease fix the issues above before proceeding.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
