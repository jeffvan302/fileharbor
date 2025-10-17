#!/usr/bin/env python3
"""
Example: Synchronous FileHarbor Client

Demonstrates using the synchronous FileHarborClient API.
"""

from fileharbor import FileHarborClient, create_console_progress_callback


def main():
    # Load client configuration
    config_path = 'client_config.json'
    
    # Create client with context manager (auto connect/disconnect)
    with FileHarborClient(config_path) as client:
        print("✅ Connected to FileHarbor server")
        
        # Upload a file with progress
        print("\n📤 Uploading file...")
        client.upload(
            'local_file.txt',
            'remote_file.txt',
            show_progress=True,
            resume=True
        )
        print("✅ Upload complete")
        
        # Download a file with custom callback
        print("\n📥 Downloading file...")
        
        def my_progress_callback(progress):
            print(f"Downloaded: {progress.percentage:.1f}% @ {progress.transfer_rate_mbps:.2f} Mbps")
        
        client.download(
            'remote_file.txt',
            'downloaded_file.txt',
            progress_callback=my_progress_callback,
            resume=True
        )
        print("✅ Download complete")
        
        # List files
        print("\n📂 Listing files...")
        files = client.list_directory('/', recursive=True)
        for file in files:
            if file.is_directory:
                print(f"  📁 {file.path}/")
            else:
                size_mb = file.size / (1024 * 1024)
                print(f"  📄 {file.path} ({size_mb:.2f} MB)")
        
        # Get file info
        print("\n📊 File statistics...")
        file_info = client.stat('remote_file.txt')
        print(f"  Path: {file_info.path}")
        print(f"  Size: {file_info.size} bytes")
        print(f"  Checksum: {file_info.checksum}")
        
        # Create directory
        print("\n📁 Creating directory...")
        client.mkdir('new_folder')
        print("✅ Directory created")
        
        # Check if file exists
        exists = client.exists('remote_file.txt')
        print(f"\n🔍 File exists: {exists}")
        
        # Rename file
        print("\n📝 Renaming file...")
        client.rename('remote_file.txt', 'renamed_file.txt')
        print("✅ File renamed")
        
        # Delete file
        print("\n🗑️  Deleting file...")
        client.delete('renamed_file.txt')
        print("✅ File deleted")
        
        # Get complete manifest
        print("\n📋 Getting manifest...")
        manifest = client.get_manifest()
        print(f"✅ Total files: {len(manifest)}")
        
        print("\n👋 Done!")


if __name__ == '__main__':
    main()
