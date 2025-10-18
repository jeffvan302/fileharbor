#!/usr/bin/env python3
"""
Example: Asynchronous FileHarbor Client

Demonstrates using the AsyncFileHarborClient API.
"""

import asyncio

from fileharbor import AsyncFileHarborClient


async def main():
    # Load client configuration
    config_path = "client_config.json"

    # Create async client with context manager
    async with AsyncFileHarborClient(config_path) as client:
        print("✅ Connected to FileHarbor server")

        # Upload a file
        print("\n📤 Uploading file...")
        await client.upload_async("local_file.txt", "remote_file.txt", show_progress=True)
        print("✅ Upload complete")

        # Download a file
        print("\n📥 Downloading file...")
        await client.download_async("remote_file.txt", "downloaded_file.txt", show_progress=True)
        print("✅ Download complete")

        # List files
        print("\n📂 Listing files...")
        files = await client.list_directory_async("/", recursive=True)
        for file in files:
            if file.is_directory:
                print(f"  📁 {file.path}/")
            else:
                size_mb = file.size / (1024 * 1024)
                print(f"  📄 {file.path} ({size_mb:.2f} MB)")

        # Create directory
        print("\n📁 Creating directory...")
        await client.mkdir_async("async_folder")
        print("✅ Directory created")

        # Check if file exists
        exists = await client.exists_async("remote_file.txt")
        print(f"\n🔍 File exists: {exists}")

        # Get manifest
        print("\n📋 Getting manifest...")
        manifest = await client.get_manifest_async()
        print(f"✅ Total files: {len(manifest)}")

        # Ping server
        alive = await client.ping_async()
        print(f"\n💓 Server alive: {alive}")

        print("\n👋 Done!")


async def parallel_downloads():
    """Example: Download multiple files in parallel."""
    config_path = "client_config.json"

    async with AsyncFileHarborClient(config_path) as client:
        print("📥 Downloading multiple files in parallel...")

        # Create tasks for parallel downloads
        tasks = [
            client.download_async("file1.txt", "local_file1.txt"),
            client.download_async("file2.txt", "local_file2.txt"),
            client.download_async("file3.txt", "local_file3.txt"),
        ]

        # Wait for all downloads to complete
        await asyncio.gather(*tasks)

        print("✅ All downloads complete!")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())

    # Uncomment to run parallel example
    # asyncio.run(parallel_downloads())
