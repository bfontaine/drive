import argparse
from drive.client import Client


def main():
    parser = argparse.ArgumentParser(description="Script for uploading file into folder")
    parser.add_argument("--output", "-o", help="Target folder identifier.", required=True)
    parser.add_argument("--file", "-f", nargs="+", help="Files to upload", required=True)
    args = parser.parse_args()

    c = Client()

    for file_to_upload in args.file:
        new_file = c.upload_file(
            parent_id=args.output,
            path=file_to_upload,
            supports_all_drives=True
        )
        print(f"File uploaded: {new_file}")


if __name__ == "__main__":
    main()
