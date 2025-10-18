from fileharbor import FileHarborClient

# Connect and use
with FileHarborClient("cli_config.json") as client:
    # Upload file
    client.upload("local.txt", "remote.txt", show_progress=True)

    # Download file
    client.download("remote.txt", "copy.txt", show_progress=True)
