"""
Test Runner Script for MCP Agent Vulnerability Scanner
Executes comprehensive security scanning on all 4 benchmark agents.
Run this script to validate the scanner on known vulnerable agents.

Usage:
    python test_runner.py

Setup:
    1. WSL or Linux environment
    2. python -m venv venv
    3. source venv/bin/activate
    4. pip install -r requirements.py
    5. python test_runner.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Set required environment variables
os.environ.setdefault("PYTHONPATH", str(project_root))


def run_server_test():
    """
    Test the FastAPI server by making requests to all endpoints.
    """
    import asyncio
    import time
    
    print("\n" + "=" * 80)
    print("STARTING FASTAPI SERVER TEST")
    print("=" * 80)
    
    # Start server in background
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        import requests
        
        # Test health endpoint
        print("\n1. Testing health endpoint...")
        response = requests.get("http://127.0.0.1:8000/api/v1/scan/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test benchmark endpoints
        print("\n2. Testing benchmark endpoints...")
        agents = ["web_scraper", "database_query", "filesystem", "process_execution"]
        
        for agent in agents:
            print(f"\n   Testing {agent}...")
            response = requests.get(f"http://127.0.0.1:8000/api/v1/scan/scan_benchmark/{agent}", timeout=120)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Issues found: {data.get('issues_count', 0)}")
            else:
                print(f"   Error: {response.text}")
        
        # Test all benchmarks at once
        print("\n3. Testing all benchmarks endpoint...")
        response = requests.get("http://127.0.0.1:8000/api/v1/scan/scan_all_benchmarks", timeout=300)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total issues: {data.get('total_issues_found', 0)}")
        
        print("\n" + "=" * 80)
        print("SERVER TEST COMPLETE")
        print("=" * 80)
    
    finally:
        # Stop server
        print("\nStopping server...")
        server_process.terminate()
        server_process.wait(timeout=5)


def run_benchmark_test():
    """
    Run the benchmark test suite directly.
    """
    print("\n" + "=" * 80)
    print("RUNNING BENCHMARK TEST SUITE")
    print("=" * 80)
    
    try:
        from app.benchmarks_testers.agent_benchmark import BenchmarkTestSuite
        
        suite = BenchmarkTestSuite()
        suite.run_all_tests()
        suite.save_results()
        
        print("\n" + suite.generate_report())
        
    except Exception as e:
        print(f"Error running benchmark: {str(e)}")
        import traceback
        traceback.print_exc()


def verify_installation():
    """
    Verify that all required packages are installed.
    """
    print("\n" + "=" * 80)
    print("VERIFYING INSTALLATION")
    print("=" * 80)
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "requests",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.py")
        return False
    
    print("\nAll required packages installed!")
    return True


def main():
    """
    Main test runner entry point.
    """
    print("\n" + "=" * 80)
    print("MCP AGENT VULNERABILITY SCANNER - TEST SUITE")
    print("=" * 80)
    
    # Verify installation
    if not verify_installation():
        print("\nSkipping tests due to missing dependencies.")
        sys.exit(1)
    
    # Run benchmark tests
    run_benchmark_test()
    
    # Optionally run server tests
    try:
        print("\nWould you like to test the FastAPI server? (requires manual confirmation)")
        print("Skipping server test in automated mode.")
    except:
        pass


if __name__ == "__main__":
    main()
