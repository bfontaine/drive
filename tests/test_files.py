# -*- coding: UTF-8 -*-

from drive.files import File
from drive import mimetypes


def test_name():
    name = "Foo Bar"
    file = File({"id": "xx", "name": name})
    assert file.name == name


def test_is_directory():
    assert File({"id": "xx"}).is_directory is None
    assert not File({"id": "xx", "mimeType": "something"}).is_directory
    assert not File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FILE}).is_directory
    assert File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}).is_directory


def test_human_type():
    assert File({"id": "xx"}).human_type == "?"
    assert File({"id": "xx", "name": "foo.json"}).human_type == "?"
    assert File({"id": "xx", "name": "foo.jsons"}).human_type == "JSONS"
    assert File({"id": "xx", "name": "foo.jsons", "mimeType": mimetypes.JSON}).human_type == "JSON"
    assert File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}).human_type == "folder"


def test_exists():
    assert File({"id": "xx"}).exists() is None
