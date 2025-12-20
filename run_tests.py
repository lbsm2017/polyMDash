#!/usr/bin/env python
"""
Run all tests for the Polymarket Dashboard.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py -k test_name # Run specific test
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Run pytest with appropriate arguments."""
    
    # Get project root directory
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    
    # Build pytest command
    pytest_args = [
        "pytest",
        str(tests_dir),
        "-v",  # Verbose
        "--tb=short",  # Shorter traceback format
        "--color=yes",  # Colored output
    ]
    
    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    
    print("=" * 70)
    print("Running Polymarket Dashboard Test Suite")
    print("=" * 70)
    print(f"\nTests directory: {tests_dir}")
    print(f"Command: {' '.join(pytest_args)}\n")
    print("=" * 70)
    
    # Run pytest
    try:
        result = subprocess.run(pytest_args, cwd=project_root)
        return result.returncode
    except FileNotFoundError:
        print("\n❌ Error: pytest not found!")
        print("\nPlease install pytest:")
        print("  pip install pytest pytest-asyncio")
        return 1


if __name__ == "__main__":
    sys.exit(main())
