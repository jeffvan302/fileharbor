#!/usr/bin/env python3
"""
FileHarbor Test Runner

Runs all tests with coverage reporting.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py integration  # Run integration tests only
    python run_tests.py security     # Run security tests only
    python run_tests.py e2e          # Run end-to-end tests only
"""

import sys
import subprocess
from pathlib import Path


def run_tests(test_type='all'):
    """
    Run tests with pytest.
    
    Args:
        test_type: Type of tests to run ('all', 'integration', 'security', 'e2e')
    """
    project_root = Path(__file__).parent
    tests_dir = project_root / 'tests'
    
    # Base pytest command
    cmd = ['pytest', '-v', '--tb=short']
    
    # Add test directory based on type
    if test_type == 'all':
        cmd.append(str(tests_dir))
    elif test_type == 'integration':
        cmd.append(str(tests_dir / 'test_integration'))
    elif test_type == 'security':
        cmd.append(str(tests_dir / 'test_security'))
    elif test_type == 'e2e':
        cmd.append(str(tests_dir / 'test_e2e'))
    elif test_type == 'common':
        cmd.append(str(tests_dir / 'test_common'))
    else:
        print(f"Unknown test type: {test_type}")
        print("Valid types: all, integration, security, e2e, common")
        return 1
    
    # Add coverage if running all tests
    if test_type == 'all':
        cmd.extend([
            '--cov=fileharbor',
            '--cov-report=html',
            '--cov-report=term'
        ])
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run tests
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        if test_type == 'all':
            print("\n📊 Coverage report generated: htmlcov/index.html")
    else:
        print("\n❌ Some tests failed")
    
    return result.returncode


def main():
    """Main entry point."""
    test_type = sys.argv[1] if len(sys.argv) > 1 else 'all'
    sys.exit(run_tests(test_type))


if __name__ == '__main__':
    main()
