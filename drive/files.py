# -*- coding: UTF-8 -*-

import io
import json

from drive import mimetypes


class File:
    """
    A file on Google Drive. This might be a directory as well.
    """

    def __init__(self, attrs, client=None):
        """

        :param attrs:
        :param client:
        """
        # If one calls File(File(...)) make the outer file copy the attributes
        # of the inner one
        if isinstance(attrs, File):
            for attr in ("id", "_name", "kind", "mimetype", "size", "parents", "_client"):
                setattr(self, attr, getattr(attrs, attr))
            return

        self.id = attrs["id"]
        self._name = attrs.get("name")
        self.kind = attrs.get("kind")
        self.mimetype = attrs.get("mimeType")
        self.parents_ids = attrs.get("parents")

        self.size = attrs.get("size")
        if self.size:
            self.size = int(self.size)

        self._client = client

    @property
    def name(self):
        if self._name is None and self._client:
            me = self._client.get_file_metadata(self.id, False)
            if me:
                self._name = me["name"]

        return self._name

    @property
    def is_directory(self):
        if self.mimetype is None:
            return None
        return self.mimetype == mimetypes.GOOGLE_DRIVE_FOLDER

    @property
    def human_type(self):
        """
        Human-friendly file type.
        :return:
        """
        aliases = {
            mimetypes.GOOGLE_DRIVE_FOLDER: "folder",
            mimetypes.GOOGLE_SHEETS: "Google Spreadsheet",
            mimetypes.JSON: "JSON",
        }

        if self.mimetype in aliases:
            return aliases[self.mimetype]

        if self.name.lower().endswith(".jsons"):
            return "JSONS"

        return self.mimetype or "?"

    def exists(self):
        """
        Test if the file exists.
        :return:
        """
        if not self._client:
            return False

        return bool(self._client.get_file(self.id, raise_if_not_found=False))

    def unlink(self):
        """
        Remove the file. If it's a directory all its children are removed as well.
        :return: a boolean indicating success
        """
        if not self._client:
            return False

        # "If successful, this method returns an empty response body."
        # https://developers.google.com/drive/v3/reference/files/delete
        return self._client.remove_file(self.id) == ""

    def rename(self, new_name):
        """
        Rename the file.
        :param new_name:
        :return:
        """
        if not self._client:
            return False
        m = self._client.update_file(self.id, name=new_name)
        self._update(m)

    def move_in(self, new_parent, new_name=None):
        """
        Move the file under a new parent.
        :param new_parent:
        :param new_name:
        :return:
        """
        if new_parent.is_directory is False:
            raise NotADirectoryError(new_parent.name)

        parents_ids = [new_parent.id]
        kw = {
            "add_parents_ids": parents_ids,
            "remove_parents_ids": [p.id for p in self.parents()],
        }
        if new_name:
            kw["name"] = new_name

        m = self._client.update_file(self.id, **kw)
        self._update(m)
        self.parents_ids = parents_ids

    def list(self):
        """
        List a directory's content. This returns an empty list for simple files.
        :return:
        """
        if not self._client or not self.is_directory:
            return []

        return self._client.list_files(parents_in=self.id)

    def create_folder(self, name):
        """
        Create a folder under a directory. This has no effect if the file is not a directory.
        :param name:
        :return:
        """
        if not self._client or not self.is_directory:
            return False

        return self._client.create_folder(name, self.id)

    def get_or_create_folder(self, name):
        """

        :param name:
        :return:
        """
        if not self._client or not self.is_directory:
            return False

        return self._client.get_or_create_folder(name, self.id)

    def get_child(self, name):
        """

        :param name:
        :return:
        """
        if not self._client or not self.is_directory:
            return False

        return self._client.get_file(name, self.id)

    def parents(self):
        """
        Return all parents of a file.
        Note that a file can have multiple parents on Google Drive.
        :return:
        """
        if self.parents_ids is None:
            if not self._client:
                return []

            m = self._client.get_file_metadata(self.id, fields="parents")
            if not m:
                self.parents_ids = []
                return []

            self.parents_ids = m["parents"]

        parents = []
        for pid in self.parents_ids:
            parents.append(File({
                "id": pid,
                "mimetype": mimetypes.GOOGLE_DRIVE_FOLDER,
            }, client=self._client))

        return parents

    def parent(self):
        """
        Return the first parent of a file.
        :return:
        """
        ps = self.parents()
        if not ps:
            return None
        return ps[0]

    def download(self, writer, mime_type=None):
        """

        :param writer:
        :param mime_type:
        :return:
        """
        if not self._client:
            return False
        return self._client.download(self.id, writer, mime_type=mime_type)

    def download_file(self, path, mime_type=None):
        """

        :param path:
        :param mime_type:
        :return:
        """
        if not self._client:
            return False
        return self._client.download_file(self.id, path, mime_type=mime_type)

    def download_workbook(self):
        """

        :return:
        """
        if not self._client:
            return False
        return self._client.download_excel_workbook(self.id)

    def get_bytes(self, mime_type=None):
        """
        Return a ``io.BytesIO`` object holding the content of the file. This can be used as a binary reader.
        :param mime_type:
        :return:
        """
        fh = io.BytesIO()
        self.download(fh, mime_type=mime_type)
        fh.seek(0)
        return fh

    def json(self):
        """
        Convenient method to download a file as JSON.
        :return:
        """
        return json.load(self.get_bytes())

    def jsons(self):
        """
        Convenient method to download a file as a newline-delimited list of JSON objects. This returns a generator.
        :return:
        """
        line = True
        b = self.get_bytes()
        while line:
            line = b.readline()
            if line:  # skip empty lines
                yield json.loads(line.decode("utf-8"))

    def to_dict(self):
        """
        Return the file’s metadata as a dict. Mandatory keys: ``"id"``, ``"name"``. Optional ones: ``"parents"``.
        :return:
        """
        d = {
            # Add other fields as needed
            "id": self.id,
            "name": self._name,
        }
        if self.parents_ids:
            d["parents"] = self.parents_ids

        return d

    def __str__(self):
        return self.name

    def __repr__(self):
        klass = self.__class__
        dir_info = " (directory)" if self.is_directory else ""
        return "<%s.%s name=\"%s\"%s>" % (
            klass.__module__, klass.__name__, self.__str__(), dir_info)

    # Allow files to be sorted
    def __lt__(self, other):
        return str(self) < str(other)

    # Private API

    def _update(self, attrs):
        """
        Update the current file instance with an attributes dict.
        :param attrs:
        :return:
        """
        if not attrs:
            return
        if isinstance(attrs, File):
            attrs = attrs.to_dict()

        # Add other fields as needed
        name = attrs.get("name")
        if name:
            self._name = name

        parents = attrs.get("parents")
        if parents:
            self.parents_ids = parents
