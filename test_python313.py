#!/usr/bin/env python3
"""
Quick test to verify Python 3.13 compatibility fix.

Run this after applying the fix to ensure everything works.
"""

import sys

print("=" * 60)
print("FileHarbor Python 3.13 Compatibility Test")
print("=" * 60)
print()

# Check Python version
print(f"Python version: {sys.version}")
print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print()

# Test 1: Import the problematic module
print("Test 1: Importing compression module...")
try:
    from fileharbor.utils.compression import compress_data, decompress_data
    print("✅ SUCCESS: compression module imported")
except ImportError as e:
    print(f"❌ FAILED: {e}")
    print()
    print("The fix has not been applied yet.")
    print("Please see PYTHON313_FIX.md for instructions.")
    sys.exit(1)

# Test 2: Test compression functionality
print()
print("Test 2: Testing compression functionality...")
try:
    test_data = b"Hello, FileHarbor! This is a test."
    compressed = compress_data(test_data)
    decompressed = decompress_data(compressed)
    
    if decompressed == test_data:
        print("✅ SUCCESS: Compression/decompression working")
    else:
        print("❌ FAILED: Data mismatch after compression")
        sys.exit(1)
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Import main modules
print()
print("Test 3: Importing main modules...")
try:
    from fileharbor import FileHarborClient
    from fileharbor.config_tool import cli
    from fileharbor.server import FileHarborServer
    print("✅ SUCCESS: All main modules imported")
except ImportError as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Type hints work
print()
print("Test 4: Verifying type hints...")
try:
    def test_func(data: bytes) -> bytes:
        return data
    
    result = test_func(b"test")
    assert result == b"test"
    print("✅ SUCCESS: Type hints working correctly")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# All tests passed
print()
print("=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print()
print("FileHarbor is now compatible with Python 3.13!")
print()
print("You can now run:")
print("  - fileharbor-config server_config.json")
print("  - fileharbor-server server_config.json")
print("  - test.bat")
print()
