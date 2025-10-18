from fileharbor import FileHarborClient

# Connect and use
with FileHarborClient("client_config.json", password="testtest") as client:
    # Upload file
    client.upload("pic_test.png", "remote_pic.png", show_progress=True)

    # Download file
    client.download("remote_pic.png", "copy_pic.png", show_progress=True)
    # List files in root directory
    files = client.list_directory("/", recursive=True)
    print("Files in root directory:", files)
