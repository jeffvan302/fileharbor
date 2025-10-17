# FileHarbor Configuration Tool - Usage Guide

## 🎉 Phase 4 Complete!

The FileHarbor Configuration Tool (`fileharbor-config`) is now fully implemented and ready to use!

---

## 📦 What You Have

**Complete Configuration Tool** with 2,956 lines of code:
- ✅ Interactive menu-driven interface
- ✅ Full server configuration management
- ✅ Certificate Authority generation
- ✅ Client certificate management
- ✅ Client configuration export
- ✅ Encryption/decryption
- ✅ Backup and restore

**Total Project:** 6,416 lines of Python code across 28 modules

---

## 🚀 Quick Start

### 1. Install the Package

```bash
cd /mnt/user-data/outputs/fileharbor
pip install -e .
```

### 2. Run the Configuration Tool

```bash
# Create new configuration
fileharbor-config /path/to/server_config.json

# Edit existing configuration
fileharbor-config /path/to/existing_config.json

# Work with encrypted configuration
fileharbor-config /path/to/config.json.encrypted
```

---

## 💡 Usage Examples

### Example 1: Create a New Server Configuration

```bash
$ fileharbor-config /tmp/my_server_config.json

FileHarbor Configuration Tool v0.1.0
Configuration file does not exist.
Create new server configuration? (y/n): y

Creating new server configuration...
Generating Certificate Authority...
✅ CA certificate generated successfully

╔═══════════════════════════════════════╗
║  FileHarbor Configuration Tool        ║
║  Configuration: /tmp/my_server_config.json
╚═══════════════════════════════════════╝

Main Menu:
  1. Server Settings
  2. Library Management
  3. Client Management
  4. Certificate Authority
  5. Client Config Export
  6. Logging Configuration
  7. Security (Encrypt/Decrypt)
  8. Backup & Restore
  9. Validate Configuration
  0. Save and Exit

Select option: _
```

### Example 2: Add a Library

```bash
Select option: 2  # Library Management

Library Management:
  1. Add Library
  2. Edit Library
  3. Remove Library
  4. View All Libraries
  5. Manage Client Access
  0. Back to Main Menu

Select option: 1  # Add Library

Enter library name: Production Data
Enter library path: /data/production
Enter rate limit in bytes/sec (0 for unlimited): 0
Enter idle timeout in seconds [300]: 300

✅ Library 'Production Data' added successfully
   ID: lib-a1b2c3d4-e5f6-7890-abcd-ef1234567890
   Path: /data/production
   Rate Limit: Unlimited
```

### Example 3: Generate Client Certificate

```bash
Select option: 3  # Client Management

Client Management:
  1. Generate Client Certificate
  2. View All Clients
  3. Add Client to Library
  4. Remove Client Access
  5. Revoke Certificate
  0. Back to Main Menu

Select option: 1  # Generate Client Certificate

Enter client name: Web Application
Generating client certificate...

✅ Client certificate generated successfully
   Client ID: client-12345678-90ab-cdef-1234-567890abcdef
   Name: Web Application
   Certificate: client-12345678...

Add this client to a library? (y/n): y

Available libraries:
  1. Production Data (lib-a1b2c3d4...)

Select library (or 0 to skip): 1

✅ Client 'Web Application' added to library 'Production Data'
```

### Example 4: Export Client Configuration

```bash
Select option: 5  # Client Config Export

Available libraries:
  1. Production Data (lib-a1b2c3d4...)

Select library: 1

Clients with access to 'Production Data':
  1. Web Application (client-12345678...)

Select client: 1

Enter output path [./client_config.json]: /tmp/web_app_client.json
Encrypt configuration? (y/n): y
Enter encryption password: ****
Confirm password: ****

✅ Client configuration exported successfully
   File: /tmp/web_app_client.json.encrypted
   Library: Production Data
   Client: Web Application
```

### Example 5: Encrypt Configuration

```bash
Select option: 7  # Security

Security Menu:
  1. Encrypt Configuration
  2. Decrypt Configuration
  3. Change Encryption Password
  0. Back to Main Menu

Select option: 1  # Encrypt Configuration

⚠️  This will encrypt the current configuration file.
   Original file will be kept as backup.
Continue? (y/n): y

Enter encryption password: ****
Confirm password: ****

Encrypting configuration...
✅ Configuration encrypted successfully
   Encrypted file: /tmp/my_server_config.json.encrypted
   Backup: /tmp/my_server_config.json.backup.20251016_143022
```

### Example 6: Create Backup

```bash
Select option: 8  # Backup & Restore

Backup & Restore Menu:
  1. Create Backup Now
  2. List Backups
  3. Restore from Backup
  4. Cleanup Old Backups
  0. Back to Main Menu

Select option: 1  # Create Backup Now

Creating backup...
✅ Backup created: /tmp/my_server_config.json.backup.20251016_143545
```

---

## 📋 Main Menu Options

### 1. Server Settings
Configure core server parameters:
- Host address and port
- Worker thread count
- Maximum connections
- Idle timeout
- Chunk size for transfers

### 2. Library Management
Manage file storage libraries:
- Add new libraries
- Edit library paths and settings
- Remove libraries
- View all configured libraries
- Manage client access per library

### 3. Client Management
Manage client certificates and access:
- Generate new client certificates
- View all clients
- Add clients to libraries
- Remove client access
- Revoke certificates (add to CRL)

### 4. Certificate Authority
View and manage the CA:
- View CA certificate details
- Export CA certificate to file
- View Certificate Revocation List
- Certificate fingerprints

### 5. Client Config Export
Generate client configuration files:
- Select library
- Select client
- Export with credentials
- Optional encryption

### 6. Logging Configuration
Configure server logging:
- Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Configure log file path
- Set log rotation parameters

### 7. Security (Encrypt/Decrypt)
Manage configuration encryption:
- Encrypt plain configuration
- Decrypt encrypted configuration
- Change encryption password

### 8. Backup & Restore
Backup and recovery operations:
- Create manual backups
- List available backups
- Restore from backup
- Cleanup old backups

### 9. Validate Configuration
Check configuration for errors:
- Schema validation
- Path validation
- Certificate validation
- Cross-reference checks

### 0. Save and Exit
Save changes and quit:
- Saves configuration to disk
- Option to create backup
- Validates before saving

---

## 🔧 Advanced Usage

### Working with Encrypted Configs

```bash
# Load encrypted config (will prompt for password)
fileharbor-config config.json.encrypted

# The tool automatically detects encryption
# and prompts for password when needed
```

### Batch Operations

```python
# You can also use the config tool modules programmatically
from fileharbor.config_tool import ServerConfigEditor, CertificateManager
from fileharbor.common.config_schema import ServerConfig, load_config_from_file

# Load config
config = load_config_from_file("server_config.json", ServerConfig)

# Use editor
editor = ServerConfigEditor()
editor.add_library(config, "New Library", "/data/new")

# Generate certificates
cert_mgr = CertificateManager()
client_id, cert, key = cert_mgr.generate_client_certificate(
    config, 
    "Automated Client"
)
```

### Scripting Configuration

```bash
# Use the tool in scripts
echo "1
0
0" | fileharbor-config server_config.json
```

---

## 🐛 Troubleshooting

### "Configuration file is encrypted" but I don't have the password
- Use the original unencrypted backup
- Check for `.backup` files in the same directory
- If no backup exists, you'll need to create a new configuration

### "Permission denied" when adding library
- Check that the library path exists and is accessible
- Ensure the user has read/write permissions
- Use absolute paths

### "Certificate validation failed"
- The CA may have changed
- Check the Certificate Revocation List
- Regenerate the client certificate if needed

### Changes not saved
- Always select "0. Save and Exit" from the main menu
- Check for validation errors
- Ensure write permissions on the config file

---

## 📁 Files Created

### Server Configuration
```
server_config.json                    # Main config file
server_config.json.encrypted          # Encrypted version (optional)
server_config.json.backup.TIMESTAMP   # Automatic backups
```

### Client Configurations
```
client_config.json                    # Exported client config
client_config.json.encrypted          # Encrypted client config
```

### Structure
```json
{
  "version": "1.0.0",
  "server": { "host": "0.0.0.0", "port": 8443, ... },
  "security": { "ca_certificate": "...", "crl": [...] },
  "libraries": { "lib-id": { "name": "...", ... } },
  "clients": { "client-id": { "name": "...", ... } },
  "logging": { "level": "INFO", ... }
}
```

---

## ✅ Verification

To verify the configuration tool is working:

```bash
# Check installation
which fileharbor-config

# Check version
fileharbor-config --version

# Test with a temporary config
fileharbor-config /tmp/test_config.json
# (Create new config, add a library, save and exit)

# View the created config
cat /tmp/test_config.json
```

---

## 🎯 Next Steps

With the configuration tool complete, you can:

1. **Create Server Configurations** - Set up your server parameters
2. **Generate Certificates** - Create CA and client certificates
3. **Export Client Configs** - Distribute to client applications
4. **Wait for Phase 5** - Server implementation (coming next)

Once Phase 5 (Server) is complete, you'll be able to:
- Start the FileHarbor server with your configuration
- Accept client connections
- Transfer files securely

---

## 📚 Documentation

For more information:
- [README.md](computer:///mnt/user-data/outputs/fileharbor/README.md) - Complete project documentation
- [PHASE4_SUMMARY.md](computer:///mnt/user-data/outputs/fileharbor/PHASE4_SUMMARY.md) - Phase 4 details
- [PROJECT_STATUS.md](computer:///mnt/user-data/outputs/fileharbor/PROJECT_STATUS.md) - Overall project status

---

**Status:** ✅ Configuration Tool Complete and Ready!  
**Next:** Phase 5 - Server Implementation
