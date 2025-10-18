from fileharbor import FileHarborClient

# Connect and use
with FileHarborClient("client_config.json") as client:
    # Upload file
    client.upload("pic_test.png", "remote_pic.png", show_progress=True)

    # Download file
    client.download("remote_pic.png", "copy_pic.png", show_progress=True)
