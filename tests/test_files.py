# -*- coding: UTF-8 -*-
import io

import pytest

from drive import mimetypes, Client
from drive.files import File, guess_original_mime_type


def test_name():
    name = "Foo Bar"
    file = File({"id": "xx", "name": name})
    assert file.name == name


def test_is_directory():
    assert File({"id": "xx"}).is_directory is None
    assert not File({"id": "xx", "mimeType": "something"}).is_directory
    assert not File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FILE}).is_directory
    assert File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}).is_directory


@pytest.mark.parametrize("attrs, expected", [
    ({"id": "xx"}, "?"),
    ({"id": "xx", "name": "foo.json"}, "?"),
    ({"id": "xx", "name": "foo.jsons"}, "JSONS"),
    ({"id": "xx", "name": "foo.jsons", "mimeType": mimetypes.JSON}, "JSON"),
    ({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}, "folder"),
])
def test_human_type(attrs, expected):
    file = File(attrs)
    setattr(file, "_fetched_name", True)
    assert file.human_type == expected


def test_exists():
    class FakeClient(Client):
        def get_file(self, file_id, *, raise_if_not_found=True):
            return File({"id": file_id}) if file_id == "yes" else None

    client = FakeClient()

    file1 = File({"id": "yes"}, client=client)
    file2 = File({"id": "no"}, client=client)

    assert file1.exists()
    assert not file2.exists()


try:
    import magic
except ImportError:
    import warnings

    warnings.warn("Libmagic is not installed; cannot properly test guess_original_mime_type")


    def test_guess_mime_type_raise():
        r = io.BytesIO()
        r.write(b"foobar")
        r.seek(0)
        with pytest.raises(RuntimeError):
            guess_original_mime_type(r)

else:
    def test_guess_mime_type_preserve_reader_position():
        r = io.BytesIO()
        r.write(b"foobar")
        offset = 4
        r.seek(offset)
        guess_original_mime_type(r)
        assert r.tell() == offset
