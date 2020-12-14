import argparse
from drive.client import Client


def main():
    parser = argparse.ArgumentParser(description="Script for download file or folder")
    parser.add_argument("--input", "-i", help="Target file/folder to download", required=True)
    parser.add_argument("--output", "-o", help="Output folder to store downloaded files", required=True)
    args = parser.parse_args()

    c = Client()
    d = c.get_file(
        file_id=args.input,
        supports_all_drives=True
    )

    if d.is_directory:
        for file_to_download in d.list():
            print(f"Downloading: {file_to_download.name}")
            file_to_download.download_file(f"{args.output}/{file_to_download.name}")
            print(f"  Done")
    else:
        print(f"Downloading: {d.name}")
        d.download_file(f"{args.output}/{d.name}")
        print("  Done")

if __name__ == "__main__":
    main()
