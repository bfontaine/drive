# -*- coding: UTF-8 -*-

import io
import json
from typing import Optional, Union, cast, Dict, List, Any, BinaryIO, Iterable, Iterator

from openpyxl.workbook import Workbook

import drive
from drive import mimetypes

__all__ = ["File", "guess_original_mime_type"]

HUMAN_TYPES = {
    mimetypes.GOOGLE_DRIVE_FOLDER: "folder",
    mimetypes.GOOGLE_SHEETS: "Google Spreadsheet",
    mimetypes.JSON: "JSON",
}


class File:
    """
    A file on Google Drive. This might be a directory as well.
    """

    def __init__(self, attrs: Union["File", dict[Any, Any]], client: Optional["drive.Client"] = None) -> None:
        """
        Create a file object.

        :param attrs:
        :param client:
        """
        # If one calls File(File(...)) make the outer file copy the attributes of the inner one
        if isinstance(attrs, File):
            file = attrs

            if client is None:
                # noinspection PyUnresolvedReferences,PyProtectedMember
                client = file._client

            attrs = {
                attr: getattr(file, attr)
                for attr in ("id", "kind", "mimetype", "size", "parents")
            }
            attrs["name"] = file._name

        self.id: str = attrs["id"]
        self._name: Optional[str] = attrs.get("name")
        self._fetched_name = False
        self.kind: Optional[str] = attrs.get("kind")
        self.mimetype: Optional[str] = attrs.get("mimeType")
        self.parents_ids: Optional[Iterable[str]] = attrs.get("parents")

        self.size: Optional[int] = None
        size = attrs.get("size")
        if size is not None:
            self.size = int(size)

        self._client: Optional["drive.Client"] = client

    @property
    def client(self):
        assert self._client is not None, "This operation requires a Drive client"
        return self._client

    @property
    def name(self) -> Union[str, None]:
        if self._name is None and not self._fetched_name:
            me = self.client.get_file_metadata(self.id, raise_if_not_found=False)
            if me:
                self._name = cast(str, me["name"])

            self._fetched_name = True

        return self._name

    @property
    def is_directory(self) -> Optional[bool]:
        """Test if this file is a directory. Return `None` if the metadata is not set."""
        if self.mimetype is None:
            return None
        return self.mimetype == mimetypes.GOOGLE_DRIVE_FOLDER

    @property
    def human_type(self) -> str:
        """
        Human-friendly file type.
        """
        if self.mimetype in HUMAN_TYPES:
            return HUMAN_TYPES[self.mimetype]

        if self.name and self.name.lower().endswith(".jsons"):
            return "JSONS"

        return self.mimetype or "?"

    def exists(self) -> bool:
        """
        Test if the file exists.
        """
        return bool(self.client.get_file(self.id, raise_if_not_found=False))

    def unlink(self) -> bool:
        """
        Remove the file. If it's a directory all its children are removed as well.
        :return: a boolean indicating success
        """
        # "If successful, this method returns an empty response body."
        # https://developers.google.com/drive/v3/reference/files/delete
        return self.client.remove_file(self.id) == ""

    def rename(self, new_name: str) -> None:
        """
        Rename the file.
        :param new_name:
        :return:
        """
        m = self.client.update_file(self.id, name=new_name)
        self._update(m)
        return None

    def move_in(self, new_parent: "File", new_name: Optional[str] = None) -> None:
        """
        Move the file under a new parent.
        :param new_parent:
        :param new_name:
        :return:
        """
        if new_parent.is_directory is False:
            raise NotADirectoryError(new_parent.name)

        parents_ids = [new_parent.id]
        kw: dict[str, Any] = {
            "add_parents_ids": parents_ids,
            "remove_parents_ids": [p.id for p in self.parents()],
        }
        if new_name:
            kw["name"] = new_name

        m = self.client.update_file(self.id, **kw)
        self._update(m)
        self.parents_ids = parents_ids
        return None

    def list(self) -> list["File"]:
        """
        List a directory's content. This returns an empty list for simple files.
        :return:
        """
        if not self.is_directory:
            return []

        return self.client.list_files(parents_in=self.id)

    def create_folder(self, name: str) -> Optional["File"]:
        """
        Create a folder under a directory. This has no effect if the file is not a directory.
        :param name:
        :return:
        """
        if not self.is_directory:
            return None

        return self.client.create_folder(name, self.id)

    def get_or_create_folder(self, name: str) -> Optional["File"]:
        """

        :param name:
        :return:
        """
        if not self.is_directory:
            return None

        return self.client.get_or_create_folder(name, self.id)

    def grant_permissions(self, role: str, type_: str) -> Optional[Dict[str, Any]]:
        return self.client.grant_file_permissions(self.id, role, type_)

    def get_child(self, name: str) -> Optional["File"]:
        """
        Get a child file. Return None if the current file is not a directory.

        :param name:
        :return:
        """
        if not self.is_directory:
            return None

        return self.client.get_file_by_name(name, self.id)

    def parents(self) -> List["File"]:
        """
        Return all parents of a file.
        Note that a file can have multiple parents on Google Drive.
        :return:
        """
        if self.parents_ids is None:
            m = self.client.get_file_metadata(self.id, fields="parents")
            if not m:
                self.parents_ids = []
                return []

            self.parents_ids = m["parents"]

        parents: List["File"] = []
        for pid in cast(Iterable[str], self.parents_ids):
            parents.append(File({
                "id": pid,
                "mimetype": mimetypes.GOOGLE_DRIVE_FOLDER,
            }, client=self.client))

        return parents

    def parent(self) -> Optional["File"]:
        """
        Return the first parent of a file.
        :return:
        """
        ps = self.parents()
        if not ps:
            return None
        return ps[0]

    def download(self, writer: BinaryIO, mime_type: Optional[str] = None) -> None:
        """

        :param writer:
        :param mime_type:
        :return:
        """
        self.client.download(self.id, writer, mime_type=mime_type)
        return None

    def download_file(self, path: str, mime_type: Optional[str] = None) -> None:
        """

        :param path:
        :param mime_type:
        :return:
        """
        return self.client.download_file(self.id, path, mime_type=mime_type)

    def download_workbook(self, read_only: bool = False) -> Workbook:
        """

        :param read_only: set this to ``True`` if you don't plan to save or edit the workbook.
        :return:
        """
        return self.client.download_excel_workbook(self.id, read_only=read_only)

    def get_bytes(self, mime_type: Optional[str] = None) -> io.BytesIO:
        """
        Return a ``io.BytesIO`` object holding the content of the file. This can be used as a binary reader.
        :param mime_type:
        :return:
        """
        fh = io.BytesIO()
        self.download(fh, mime_type=mime_type)
        fh.seek(0)
        return fh

    def json(self) -> Any:
        """
        Download the file as JSON.
        :return:
        """
        return json.load(self.get_bytes())

    def jsons(self) -> Iterator[Any]:
        """
        Download the file as a newline-delimited list of JSON objects. This returns a generator.
        :return:
        """
        line = b'1'  # just for typing
        b = self.get_bytes()
        while line:
            line = b.readline()
            if line:  # skip empty lines
                yield json.loads(line.decode("utf-8"))

    def get_web_view_link(self) -> str:
        return self.client.get_web_view_link(self.id)

    def to_dict(self) -> dict[str, Any]:
        """
        Return the file’s metadata as a dict. Mandatory keys: ``"id"``, ``"name"``. Optional ones: ``"parents"``.
        """
        d: dict[str, Any] = {
            # Add other fields as needed
            "id": self.id,
            "name": self._name,
        }
        if self.parents_ids:
            d["parents"] = self.parents_ids

        return d

    def __str__(self) -> str:
        return self.name or super().__str__()

    def __repr__(self) -> str:
        klass = self.__class__
        dir_info = " (directory)" if self._client and self.is_directory else ""
        return "<%s.%s name=\"%s\"%s>" % (
            klass.__module__, klass.__name__, self.__str__(), dir_info)

    # Allow files to be sorted
    def __lt__(self, other) -> bool:
        return str(self) < str(other)

    # Private API

    def _update(self, attrs: Union["File", Dict[str, Any], None]) -> None:
        """
        Update the current file instance with a dict of attributes.
        :param attrs:
        :return:
        """
        if not attrs:
            return

        if isinstance(attrs, File):
            attrs = attrs.to_dict()

        attrs = cast(Dict[str, Any], attrs)

        # Add other fields as needed
        name = attrs.get("name")
        if name:
            self._name = name

        parents = attrs.get("parents")
        if parents:
            self.parents_ids = parents


def guess_original_mime_type(reader: BinaryIO) -> str:
    """
    Guess the MIME type of the content in a reader. Read 1024 bits, then seek the reader back to its original position.
    """
    try:
        import magic
    except ImportError as e:
        if str(e).startswith("failed to find libmagic"):
            raise RuntimeError("original_mime_type is None and we can't guess it because libmagic is not installed.") \
                from e
        raise

    pos = reader.tell()
    buff = reader.read(1024)
    reader.seek(pos)
    return magic.from_buffer(buff, mime=True)
