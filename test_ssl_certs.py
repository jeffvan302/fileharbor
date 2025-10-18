#!/usr/bin/env python3
"""
Test SSL certificate loading from config file.
"""

import sys
import json
import ssl
import tempfile
import os
from pathlib import Path

def test_pem_loading(pem_data, name):
    """Test if PEM data can be loaded by OpenSSL."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    # Show first and last lines
    lines = pem_data.split('\n')
    print(f"Total lines: {len(lines)}")
    print(f"First line: {repr(lines[0][:70])}")
    if len(lines) > 1:
        print(f"Last line: {repr(lines[-1][:70])}")
    
    # Check for common issues
    issues = []
    
    if '\\n' in pem_data[:50]:
        issues.append("⚠️  Contains literal '\\n' strings instead of newlines")
    
    if '\r\n' in pem_data:
        issues.append("ℹ️  Contains Windows line endings (\\r\\n)")
    elif '\r' in pem_data:
        issues.append("⚠️  Contains Mac line endings (\\r)")
    
    if not pem_data.endswith('\n'):
        issues.append("ℹ️  Does not end with newline")
    
    if issues:
        print("\nNotes:")
        for issue in issues:
            print(f"  {issue}")
    
    # Try to write to temp file and load
    print("\nAttempting to load with OpenSSL...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem', newline='') as f:
            f.write(pem_data)
            f.flush()
            temp_path = f.name
        
        print(f"  ✓ Written to temp file: {temp_path}")
        
        # Try to read it back
        with open(temp_path, 'r') as f:
            read_back = f.read()
        
        if read_back == pem_data:
            print(f"  ✓ Data matches after write/read")
        else:
            print(f"  ⚠️  Data changed after write/read")
            print(f"     Original length: {len(pem_data)}")
            print(f"     Read back length: {len(read_back)}")
        
        # Try to load with SSL library
        try:
            if 'CERTIFICATE' in pem_data:
                # Try as certificate
                context = ssl.create_default_context()
                context.load_verify_locations(temp_path)
                print(f"  ✅ Successfully loaded as CERTIFICATE")
            elif 'PRIVATE KEY' in pem_data:
                # For private key, we need a dummy cert too
                print(f"  ℹ️  Private key (cannot test alone)")
            else:
                print(f"  ⚠️  Unknown PEM type")
        except ssl.SSLError as e:
            print(f"  ❌ SSL Error: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
        finally:
            os.unlink(temp_path)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to write/load: {e}")
        return False

def test_cert_and_key(cert_pem, key_pem):
    """Test loading certificate and key together."""
    print(f"\n{'='*60}")
    print(f"Testing: Certificate + Private Key Together")
    print(f"{'='*60}")
    
    try:
        # Write both to temp files
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem', newline='') as cert_file:
            cert_file.write(cert_pem)
            cert_file.flush()
            cert_path = cert_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem', newline='') as key_file:
            key_file.write(key_pem)
            key_file.flush()
            key_path = key_file.name
        
        print(f"  ✓ Written cert to: {cert_path}")
        print(f"  ✓ Written key to: {key_path}")
        
        # Try to load both
        context = ssl.create_default_context()
        context.load_cert_chain(cert_path, key_path)
        
        print(f"  ✅ Successfully loaded certificate and key together!")
        
        os.unlink(cert_path)
        os.unlink(key_path)
        return True
        
    except ssl.SSLError as e:
        print(f"  ❌ SSL Error: {e}")
        print(f"     This usually means:")
        print(f"     - Certificate and private key don't match")
        print(f"     - Private key is encrypted/password-protected")
        print(f"     - PEM format is incorrect")
        if cert_path:
            os.unlink(cert_path)
        if key_path:
            os.unlink(key_path)
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        if cert_path:
            os.unlink(cert_path)
        if key_path:
            os.unlink(key_path)
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ssl_certs.py <config_file.json>")
        print("Example: python test_ssl_certs.py cli1_config.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    print("=" * 80)
    print("FileHarbor SSL Certificate Test")
    print("=" * 80)
    print(f"\nConfig file: {config_path}\n")
    
    # Load config
    if not Path(config_path).exists():
        print(f"❌ ERROR: File not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ ERROR: Failed to load config: {e}")
        sys.exit(1)
    
    # Get certificates
    ca_cert = config.get('server', {}).get('ca_certificate')
    client_cert = config.get('client', {}).get('certificate')
    private_key = config.get('client', {}).get('private_key')
    
    all_passed = True
    
    # Test CA certificate
    if ca_cert:
        if not test_pem_loading(ca_cert, "CA Certificate (server.ca_certificate)"):
            all_passed = False
    else:
        print("❌ ERROR: No CA certificate found in config")
        all_passed = False
    
    # Test client certificate
    if client_cert:
        if not test_pem_loading(client_cert, "Client Certificate (client.certificate)"):
            all_passed = False
    else:
        print("❌ ERROR: No client certificate found in config")
        all_passed = False
    
    # Test private key
    if private_key:
        test_pem_loading(private_key, "Private Key (client.private_key)")
        # Don't fail on private key alone test
    else:
        print("❌ ERROR: No private key found in config")
        all_passed = False
    
    # Test cert + key together
    if client_cert and private_key:
        if not test_cert_and_key(client_cert, private_key):
            all_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL SSL TESTS PASSED!")
        print("=" * 80)
        print("\nYour certificates should work. If you still get errors, check:")
        print("1. Server hostname/port are correct")
        print("2. Server is running and accessible")
        print("3. Firewall allows the connection")
    else:
        print("❌ SSL TESTS FAILED")
        print("=" * 80)
        print("\nCommon fixes:")
        print("1. Re-export the client config from the config tool")
        print("2. Make sure certificates were exported correctly")
        print("3. Check that private key is NOT password-protected")
        print("4. Verify certificate and private key match")
    
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
