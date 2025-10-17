# FileHarbor Client - Quick Start Guide

## 🎉 Phase 6 Complete!

The FileHarbor client library is fully implemented with both synchronous and asynchronous APIs!

---

## 📦 Installation

```bash
cd /mnt/user-data/outputs/fileharbor
pip install -e .
```

---

## 🚀 Quick Start

### 1. Get Client Configuration

First, you need a client configuration file. Use the config tool:

```bash
# On the server, export a client config
fileharbor-config server_config.json

# Menu: Client Config Export
# - Select library
# - Select client
# - Export to file
# Result: client_config.json
```

Or create manually:
```json
{
  "version": "1.0.0",
  "server": {
    "host": "fileserver.example.com",
    "port": 8443
  },
  "security": {
    "certificate": "-----BEGIN CERTIFICATE-----\n...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "ca_certificate": "-----BEGIN CERTIFICATE-----\n..."
  },
  "library_id": "lib-uuid-here",
  "connection": {
    "timeout": 30,
    "retry_attempts": 3
  },
  "transfer": {
    "chunk_size": 65536
  }
}
```

### 2. Basic Usage (Synchronous)

```python
from fileharbor import FileHarborClient

# Connect and use
with FileHarborClient('client_config.json') as client:
    # Upload file
    client.upload('local.txt', 'remote.txt', show_progress=True)
    
    # Download file
    client.download('remote.txt', 'copy.txt', show_progress=True)
```

### 3. Basic Usage (Asynchronous)

```python
import asyncio
from fileharbor import AsyncFileHarborClient

async def main():
    async with AsyncFileHarborClient('client_config.json') as client:
        await client.upload_async('local.txt', 'remote.txt', show_progress=True)
        await client.download_async('remote.txt', 'copy.txt', show_progress=True)

asyncio.run(main())
```

---

## 📚 Common Operations

### Upload File
```python
client.upload('local_file.txt', 'remote_file.txt', show_progress=True)
```

### Download File
```python
client.download('remote_file.txt', 'local_file.txt', show_progress=True)
```

### Upload with Retry
```python
client.upload_with_retry('important.dat', 'backup/important.dat', max_retries=5)
```

### List Directory
```python
files = client.list_directory('/documents', recursive=True)
for f in files:
    print(f"{'📁' if f.is_directory else '📄'} {f.path}")
```

### Create Directory
```python
client.mkdir('new_folder')
```

### Delete File
```python
client.delete('old_file.txt')
```

### Rename/Move File
```python
client.rename('old_name.txt', 'new_name.txt')
```

### Check if File Exists
```python
if client.exists('file.txt'):
    print("File exists!")
```

### Get File Info
```python
info = client.stat('file.txt')
print(f"Size: {info.size} bytes")
print(f"Checksum: {info.checksum}")
print(f"Modified: {info.modified_time}")
```

### Get Complete Manifest
```python
manifest = client.get_manifest()
for file in manifest:
    if not file.is_directory:
        print(f"{file.path}: {file.checksum}")
```

---

## 🎨 Progress Tracking

### Console Progress Bar
```python
client.upload('large_file.bin', 'backup.bin', show_progress=True)
# Output: Upload: [████████████████░░░░] 75.2% @ 12.5 Mbps
```

### Custom Progress Callback
```python
def my_progress(progress):
    print(f"Progress: {progress.percentage:.1f}%")
    print(f"Speed: {progress.transfer_rate_mbps:.2f} Mbps")
    if progress.eta_seconds:
        print(f"ETA: {progress.eta_seconds:.0f} seconds")

client.upload('file.dat', 'remote.dat', progress_callback=my_progress)
```

### Access Progress Details
```python
from fileharbor import TransferProgress

def detailed_callback(progress: TransferProgress):
    mb_done = progress.bytes_transferred / (1024 * 1024)
    mb_total = progress.total_bytes / (1024 * 1024)
    
    print(f"{progress.operation}: {progress.filepath}")
    print(f"  {mb_done:.2f} / {mb_total:.2f} MB ({progress.percentage:.1f}%)")
    print(f"  Rate: {progress.transfer_rate_mbps:.2f} Mbps")
    print(f"  Elapsed: {progress.elapsed_time:.1f}s")
    
    if progress.eta_seconds:
        minutes = int(progress.eta_seconds / 60)
        seconds = int(progress.eta_seconds % 60)
        print(f"  ETA: {minutes}m {seconds}s")
```

---

## ⚡ Async Operations

### Parallel Downloads
```python
import asyncio
from fileharbor import AsyncFileHarborClient

async def download_all():
    async with AsyncFileHarborClient('config.json') as client:
        # Download 3 files in parallel
        await asyncio.gather(
            client.download_async('file1.txt', 'local1.txt'),
            client.download_async('file2.txt', 'local2.txt'),
            client.download_async('file3.txt', 'local3.txt')
        )

asyncio.run(download_all())
```

### Concurrent Operations
```python
async def batch_operations():
    async with AsyncFileHarborClient('config.json') as client:
        # Upload, download, and list at the same time
        upload_task = client.upload_async('new.txt', 'new.txt')
        download_task = client.download_async('old.txt', 'old.txt')
        list_task = client.list_directory_async('/')
        
        await asyncio.gather(upload_task, download_task, list_task)
```

---

## 🔄 Resumable Transfers

### Automatic Resume
```python
# If interrupted, will resume from where it left off
client.upload('huge_file.bin', 'backup/huge_file.bin', resume=True)
```

### Manual Connection Management
```python
client = FileHarborClient('config.json')

try:
    client.connect()
    
    # Upload (with resume)
    client.upload('file.dat', 'remote.dat', resume=True)
    
    # ... more operations ...
    
finally:
    client.disconnect()
```

---

## 🛡️ Error Handling

### Handle Specific Errors
```python
from fileharbor import FileHarborClient
from fileharbor.common.exceptions import (
    FileTransferError,
    ChecksumMismatchError,
    ConnectionError,
    FileNotFoundError
)

with FileHarborClient('config.json') as client:
    try:
        client.upload('file.txt', 'remote.txt')
    except FileNotFoundError:
        print("Local file not found")
    except ChecksumMismatchError:
        print("Checksum verification failed")
    except FileTransferError as e:
        print(f"Transfer failed: {e}")
    except ConnectionError as e:
        print(f"Connection failed: {e}")
```

### Automatic Retry on Failure
```python
# Will retry up to 3 times with resume
client.upload_with_retry('important.dat', 'backup.dat', max_retries=3)
```

---

## 📁 Batch Operations

### Upload Multiple Files
```python
from pathlib import Path

with FileHarborClient('config.json') as client:
    local_dir = Path('documents')
    
    for file_path in local_dir.glob('**/*.pdf'):
        remote_path = str(file_path.relative_to(local_dir))
        
        try:
            client.upload(str(file_path), remote_path, resume=True)
            print(f"✅ Uploaded: {file_path.name}")
        except Exception as e:
            print(f"❌ Failed: {file_path.name} - {e}")
```

### Download Directory
```python
with FileHarborClient('config.json') as client:
    # Get all files in remote directory
    files = client.list_directory('/documents', recursive=True)
    
    # Download each file
    for file_info in files:
        if not file_info.is_directory:
            local_path = f"local/{file_info.path}"
            
            # Create parent directories
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download
            client.download(file_info.path, local_path, resume=True)
            print(f"✅ {file_info.path}")
```

---

## 🔐 Encrypted Configuration

### Load Encrypted Config
```python
# Will prompt for password
client = FileHarborClient('config.json.encrypted')

# Or provide password
client = FileHarborClient('config.json.encrypted', password='mypassword')
```

---

## 🧪 Test Connection

### Ping Server
```python
with FileHarborClient('config.json') as client:
    if client.ping():
        print("✅ Server is alive")
    else:
        print("❌ Server not responding")
```

---

## 📊 Complete Example

```python
#!/usr/bin/env python3
"""Complete example demonstrating all major features."""

from fileharbor import FileHarborClient
from pathlib import Path

def main():
    config_path = 'client_config.json'
    
    with FileHarborClient(config_path) as client:
        print("✅ Connected to FileHarbor server\n")
        
        # 1. Upload with progress
        print("📤 Uploading files...")
        for file in Path('upload').glob('*.txt'):
            client.upload(
                str(file),
                f"documents/{file.name}",
                show_progress=True,
                resume=True
            )
        
        # 2. Create directory structure
        print("\n📁 Creating directories...")
        client.mkdir('archives')
        client.mkdir('archives/2025')
        
        # 3. List files
        print("\n📂 Listing files...")
        files = client.list_directory('/', recursive=True)
        for f in files:
            icon = '📁' if f.is_directory else '📄'
            size = f"{f.size / 1024:.1f} KB" if not f.is_directory else ""
            print(f"  {icon} {f.path} {size}")
        
        # 4. Get manifest with checksums
        print("\n📋 Getting manifest...")
        manifest = client.get_manifest()
        print(f"✅ Total files: {len([f for f in manifest if not f.is_directory])}")
        
        # 5. Download specific files
        print("\n📥 Downloading...")
        client.download(
            'documents/important.txt',
            'download/important.txt',
            show_progress=True
        )
        
        # 6. Cleanup
        print("\n🧹 Cleanup...")
        if client.exists('old_file.txt'):
            client.delete('old_file.txt')
        
        print("\n✅ All operations completed!")

if __name__ == '__main__':
    main()
```

---

## 🎯 Next Steps

1. **Run Examples**: Try the example scripts in `/examples`
2. **Read Summaries**: Check PHASE6_SUMMARY.md for detailed documentation
3. **Start Server**: Run `fileharbor-server` to test against
4. **Build Application**: Integrate the client into your application

---

## 📚 API Reference

For complete API documentation, see:
- [PHASE6_SUMMARY.md](computer:///mnt/user-data/outputs/fileharbor/PHASE6_SUMMARY.md) - Complete client documentation
- [README.md](computer:///mnt/user-data/outputs/fileharbor/README.md) - Project overview

---

**Status:** ✅ Client Complete and Ready to Use!
