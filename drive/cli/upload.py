import argparse
from typing import List
from drive.client import Client


def main_upload(
    target_folder: str,
    files_to_upload: List[str],
    update_file: bool
):
    if not files_to_upload:
        return

    c = Client()
    for file_path in files_to_upload:
        print(f"Uploading file... {file_path}")
        new_file = c.upload_file(
            parent_id=target_folder,
            path=file_path,
            update_existing=update_file,
            supports_all_drives=True
        )
        print(f"  Done: {new_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Script for uploading file into folder"
    )
    parser.add_argument(
        "--output", "-o",
        help="Target folder identifier",
        required=True
    )
    parser.add_argument(
        "--file", "-f",
        nargs="+",
        help="Files to upload",
        required=True
    )
    parser.add_argument(
        "--update-existing", "-U",
        help="Update existing files instead of uploading new ones",
        default=False
    )
    args = parser.parse_args()

    main_upload(
        target_folder=args.output,
        files_to_upload=args.file,
        update_file=bool(args.update_exsiting)
    )


if __name__ == "__main__":
    main()
