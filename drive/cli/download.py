import os
import argparse
from typing import List
from drive.client import Client, File


def _download(
    client: Client,
    file_to_download: File,
    output_folder: str,
    recursive: bool,
    root_folder: bool = False,
):
    if file_to_download.is_directory:
        if not recursive and not root_folder:
            print(f"Recursive download not enabled, skipping '{file_to_download.name}' folder...")
            return

        print(f"Downloading folder: {file_to_download.name}/")
        if not root_folder:
            os.makedirs(os.path.join(output_folder, file_to_download.name), exist_ok=True)

        for file in file_to_download.list():
            _download(
                client=client,
                file_to_download=file,
                output_folder=output_folder if root_folder else os.path.join(output_folder, file_to_download.name),
                recursive=recursive
            )
    else:
        print(f"Downloading: {file_to_download.name}")
        file_to_download.download_file(f"{output_folder}/{file_to_download.name}")
        print("  Done")


def main_download(
    files_to_download: List[str],
    output_folder: str,
    recursive: bool
):
    c = Client()
    for file_id in files_to_download:
        gf = c.get_file(
            file_id=file_id,
            supports_all_drives=True
        )
        _download(
            client=c,
            file_to_download=gf,
            output_folder=output_folder,
            recursive=recursive,
            root_folder=True
        )


def main():
    parser = argparse.ArgumentParser(
        description="Script for download file or folder"
    )
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        help="Target file/folder to download",
        required=True
    )
    parser.add_argument(
        "--output", "-o",
        help="Output folder to store downloaded files",
        required=True
    )
    parser.add_argument(
        "--recursive", "-r",
        type=bool,
        help="If set to True, it downloads recursively",
        default=False
    )
    args = parser.parse_args()

    main_download(
        files_to_download=args.input,
        output_folder=args.output,
        recursive=bool(args.recursive)
    )


if __name__ == "__main__":
    main()
