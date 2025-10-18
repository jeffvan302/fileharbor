#!/usr/bin/env python3
"""
Diagnostic script to check client configuration and certificate format.
"""

import sys
import json
from pathlib import Path

def check_pem_format(pem_data, name):
    """Check if PEM data is properly formatted."""
    errors = []
    
    if not pem_data:
        errors.append(f"{name}: Empty or missing")
        return errors
    
    # Check for BEGIN marker
    if "-----BEGIN" not in pem_data:
        errors.append(f"{name}: Missing '-----BEGIN' marker")
    
    # Check for END marker
    if "-----END" not in pem_data:
        errors.append(f"{name}: Missing '-----END' marker")
    
    # Check for newlines
    if "\\n" in pem_data:
        errors.append(f"{name}: Contains literal '\\n' instead of actual newlines")
    
    # Count lines
    lines = pem_data.split('\n')
    if len(lines) < 3:
        errors.append(f"{name}: Too few lines ({len(lines)}). PEM should have multiple lines.")
    
    # Check if BEGIN is on its own line
    for i, line in enumerate(lines):
        if "-----BEGIN" in line:
            if line.strip() != line.strip().split(None, 1)[0] if "-----BEGIN" in line else line.strip():
                # Line has content after BEGIN marker
                pass
            break
    
    return errors

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_config.py <config_file.json>")
        print("Example: python check_config.py cli1_config.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    print("=" * 80)
    print(f"FileHarbor Config Diagnostic Tool")
    print("=" * 80)
    print(f"\nChecking: {config_path}\n")
    
    # Check file exists
    if not Path(config_path).exists():
        print(f"❌ ERROR: File not found: {config_path}")
        sys.exit(1)
    
    # Load JSON
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✓ JSON format is valid")
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to read file: {e}")
        sys.exit(1)
    
    # Check structure
    print("\nChecking configuration structure:")
    
    has_errors = False
    
    # Check version
    if 'version' in config:
        print(f"✓ Version: {config['version']}")
    else:
        print("⚠ Warning: No version field")
    
    # Check server section
    if 'server' not in config:
        print("❌ ERROR: Missing 'server' section")
        has_errors = True
    else:
        server = config['server']
        print(f"✓ Server section exists")
        
        if 'host' in server:
            print(f"  ✓ Host: {server['host']}")
        else:
            print("  ❌ ERROR: Missing server.host")
            has_errors = True
        
        if 'port' in server:
            print(f"  ✓ Port: {server['port']}")
        else:
            print("  ❌ ERROR: Missing server.port")
            has_errors = True
        
        if 'ca_certificate' in server:
            ca_cert = server['ca_certificate']
            print(f"  ✓ CA Certificate present ({len(ca_cert)} chars)")
            
            # Check CA cert format
            errors = check_pem_format(ca_cert, "CA Certificate")
            if errors:
                print("  ❌ CA Certificate format issues:")
                for error in errors:
                    print(f"     - {error}")
                has_errors = True
            else:
                print("  ✓ CA Certificate format looks good")
        else:
            print("  ❌ ERROR: Missing server.ca_certificate")
            has_errors = True
    
    # Check client section
    if 'client' not in config:
        print("❌ ERROR: Missing 'client' section")
        has_errors = True
    else:
        client = config['client']
        print(f"✓ Client section exists")
        
        if 'certificate' in client:
            cert = client['certificate']
            print(f"  ✓ Client Certificate present ({len(cert)} chars)")
            
            # Check client cert format
            errors = check_pem_format(cert, "Client Certificate")
            if errors:
                print("  ❌ Client Certificate format issues:")
                for error in errors:
                    print(f"     - {error}")
                has_errors = True
            else:
                print("  ✓ Client Certificate format looks good")
        else:
            print("  ❌ ERROR: Missing client.certificate")
            has_errors = True
        
        if 'private_key' in client:
            key = client['private_key']
            print(f"  ✓ Private Key present ({len(key)} chars)")
            
            # Check private key format
            errors = check_pem_format(key, "Private Key")
            if errors:
                print("  ❌ Private Key format issues:")
                for error in errors:
                    print(f"     - {error}")
                has_errors = True
            else:
                print("  ✓ Private Key format looks good")
        else:
            print("  ❌ ERROR: Missing client.private_key")
            has_errors = True
        
        if 'library_id' in client:
            print(f"  ✓ Library ID: {client['library_id']}")
        else:
            print("  ❌ ERROR: Missing client.library_id")
            has_errors = True
    
    # Summary
    print("\n" + "=" * 80)
    if has_errors:
        print("❌ ERRORS FOUND - Please fix the issues above")
        print("=" * 80)
        print("\nCommon fixes:")
        print("1. If you see 'Contains literal \\n': Your PEM data has escaped newlines")
        print("   FIX: Make sure PEM certificates have actual newlines, not '\\n' strings")
        print("2. If certificates are missing: Export them again from the config tool")
        print("3. If structure is wrong: Config should have 'server' and 'client' sections")
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED - Configuration looks good!")
        print("=" * 80)
        sys.exit(0)

if __name__ == '__main__':
    main()
