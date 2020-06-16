# Drive

Google Drive client.

## Usage

The API exposes a client as `drive.client.Client` that manipulates instances of
`drive.files.File`. A `File` represent a Google Drive file. Note that both
regular files and directories are represented as `File`s, and a file can have
multiple parent directories. You can check if a `File` is a directory using the
`is_directory` attribute.

Note: "Folder" is just a synonym for "Directory".

### Authentication

By default, the client reads your service account key JSON file at the location
given by the environment variable `GOOGLE_APPLICATION_CREDENTIALS`. You can
override this behavior by passing it directly:

    client = Client("/path/to/your/service-account-key.json")


See Google’s documentation on [how to create a service account key][k].

[k]: https://cloud.google.com/iam/docs/creating-managing-service-account-keys

### Client

High-level `Client` methods:

* `get_file(file_id)` (`File`)
* `get_file_by_name(name)` (`File`)
* `files_shared_with_me()` (`File` list)
* `get_shared_directory(name)` (`File`)
* `root()` (`File`)
* `upload_file(parent, path[, name])`: Upload a file
* `upload_excel_workbook(parent, name, workbook)`: Upload an `openpyxl`
  workbook in a Google spreadsheet under `parent` with the name `name`.

The client also exposes low-level methods that work on file ids.

### File

* `id` (`str`, attribute)
* `name` (`str`, attribute)
* `is_directory` (`bool`, attribute)
* `human_type` (`str`, attribute): Human-readable file type
* `exists()` (`bool`)
* `unlink()` (`bool`): Remove the file. If it's a directory, all its children
  are removed as well
* `rename(new_name)`: Rename the file
* `move_in(new_parent[, new_name])`: Move a file under another directory. It
  can also rename the file at the same time.
* `list()`: List a directory’s content
* `create_folder(name)`: Create a folder under the current one
* `get_or_create_folder(name)`: Retrieve a child folder or create it if it
  doesn’t exist
* `get_child(name)`: Return a file under the current directory.
* `parents()`: Return a file's parents
* `parent()`: Return the first parent of a file
* `download_file(path[, mime_type])`: Download the file at a given location
* `download_workbook()`: Download the file as an `openpyxl` workbook
* `json()`: Parse the file as JSON
* `jsons()`: Parse the file as JSONS (one JSON per line) and returns a generator

Methods that operate on directories (e.g. `list()`) generally have no effect if
the `File` instance is a regular file.

### Examples

```python
from drive.client import Client

# Uses credentials from the path in the environment variable
# GOOGLE_APPLICATION_CREDENTIALS.
cl = Client()

# Get the root directory
d = cl.root()
print(d.is_directory) # True
print(d.name) # e.g. "My Drive"

# Get a directory's content
for f in d.list():
    print(f.name)

# Get a shared directory
d = cl.get_shared_directory("My Shared Dir")
```

#### Spreadsheets

```python
cl = Client()

# Download
f = cl.get_file_by_name("my_sheet")
workbook = f.download_workbook() # readonly openpyxl workbook

# Upload
workbook = Workbook()
d = cl.get_shared_directory("My Shared Directory")
cl.upload_excel_workbook(d, "my_other_sheet", workbook)
```

#### Drawings

```python
cl = Client()
# download a Drawing in a png image
cl.download_file("11AASomeFileId", "localfile.png", "image/png")
```

## License

Copyright © 2016-2020 Oscaro.com

Distributed under the MIT License.
