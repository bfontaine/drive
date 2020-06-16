# -*- coding: UTF-8 -*-

import io
import os.path
import random
import sys
import time
from typing import Optional, List, Any, Tuple

import httplib2
import openpyxl
from apiclient import discovery
from apiclient.errors import HttpError
from apiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from drive import mimetypes
from drive.auth import authorize, get_credentials
from drive.exceptions import FileNotFoundException
from drive.files import File

# Retry transport and file IO errors.
RETRYABLE_ERRORS = (httplib2.HttpLib2Error, IOError)

# Number of times to retry failed downloads.
NUM_RETRIES = 5

# Number of bytes to send/receive in each request.
CHUNKSIZE = 2 * 1024 * 1024


def handle_progressless_iter(error, progressless_iters):
    if progressless_iters > NUM_RETRIES:
        print('Failed to make progress for too many consecutive iterations.')
        raise error

    sleeptime = random.random() * (2**progressless_iters)
    print('Caught exception (%s). Sleeping for %s seconds before retry #%d.'
          % (str(error), sleeptime, progressless_iters))
    time.sleep(sleeptime)


def print_with_carriage_return(s):
    """
    Internal utility to print a one-line string prefixed with a carriage return (``\\r``).
    :param s: string to print
    :return: None
    """
    sys.stdout.write('\r' + s)
    sys.stdout.flush()


class Client:
    """
    Google Drive client
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """

        :param credentials_path:
        """
        credentials = get_credentials(credentials_path)
        http = authorize(credentials)
        self.service = discovery.build('drive', 'v3', http=http)

    @property
    def _files(self):
        return self.service.files()

    def create_folder(self, name: str, parent_id: str):
        """

        :param name:
        :param parent_id:
        :return:
        """
        file_metadata = {
            "name" : name,
            "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER,
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        return self._execute_file_request(self._files.create(body=file_metadata))

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None):
        """
        Get the ID for the folder with name folder_name.
        :param folder_name:
        :param parent_id:
        :return:
        """

        folder_list = self.list_files(name_equals=folder_name,
                                      mimetype=mimetypes.GOOGLE_DRIVE_FOLDER,
                                      parents_in=parent_id,
                                      n=1)
        if folder_list:
            if len(folder_list) == 1:
                return File(folder_list[0], client=self)

            raise NameError("Unable to find folder %s" % folder_name)

        return self.create_folder(folder_name, parent_id)

    def remove_file(self, file_id: str):
        """
        Remove a file by its id.

        :param file_id:
        :return:
        """
        return self._files.delete(fileId=file_id).execute()

    def get_file_metadata(self, file_id, raise_if_not_found=True, **kw):
        """

        :param file_id:
        :param raise_if_not_found:
        :param kw:
        :return:
        """
        try:
            return self._files.get(fileId=file_id, **kw).execute()
        except HttpError as e:
            if not raise_if_not_found:
                return None
            raise e

    def get_file(self, file_id: str, raise_if_not_found=True) -> Optional[File]:
        """
        Get a file by its id.
        :param file_id:
        :param raise_if_not_found: if ``True`` (default), raise an exception if the file doesn’t exist
        :return:
        """
        fm = self.get_file_metadata(file_id, raise_if_not_found)
        if fm:
            return File(fm, client=self)

    def get_file_by_name(self, name: str, parent_id: Optional[str] = None) -> Optional[File]:
        """
        Get a file by name.
        Note that, unlike ids, names are not guaranteed to be unique: you can have multiple files with the same name
        on Google Drive.

        :param name: Drive filename
        :param parent_id: optional parent id.
        :return:
        :raise: ``drive.exceptions.FileNotFoundException`` if the file doesn’t exist
        """
        kw = dict(name_equals=name, n=1)
        if parent_id:
            kw["parents_in"] = parent_id
        ls = self.list_files(**kw)
        if not ls:
            raise FileNotFoundException(name)

        return ls[0]

    def file_exists(self,
                    name: Optional[str] = None,
                    file_id: Optional[str] = None,
                    parent_id: Optional[str] = None) -> Optional[File]:
        """
        Check if a file exists and if so returns it.

        :param name:
        :param file_id:
        :param parent_id:
        :return:
        :raise: RuntimeError if both ``name`` and ``file_id`` are ``None``.
        """
        if not name and not file_id:
            raise RuntimeError("You must provide a name or file_id")

        if file_id:
            return self.get_file(file_id, raise_if_not_found=False)

        files = self.list_files(name_equals=name, parents_in=parent_id, n=1)
        if not files:
            return
        return files[0]

    def files_shared_with_me(self) -> List[File]:
        """
        Return a list of files (and 'directories') 'shared with me'.
        :return:
        """
        return self._execute_file_request(self._files.list(q="sharedWithMe=true"))

    def get_shared_file(self, name: str,
                        is_directory: Optional[bool] = None,
                        raise_if_not_found=True) -> Optional[File]:
        """
        Retrieve a shared file.
        If ``is_directory`` is a boolean, it’s used to filter files that are (or not) directories. By default the first
        matching file is returned without checking if it’s a directory or not.

        :param name:
        :param is_directory:
        :param raise_if_not_found:
        :return:
        """
        for shared in self.files_shared_with_me():
            if shared.name == name:
                if is_directory is False and shared.is_directory:
                    continue
                if is_directory and not shared.is_directory:
                    continue

                return shared

        if raise_if_not_found:
            raise FileNotFoundException(name)

    def get_shared_directory(self, name: str) -> Optional[File]:
        """
        Retrieve a shared directory. This is a shortcut for ``get_shared_file(name, is_directory=True)``.
        :param name:
        :return:
        """
        return self.get_shared_file(name, is_directory=True)

    def root(self) -> File:
        """
        Return the root directory. Note the alias ``"root"`` works as an alias file id for the root directory.
        :return:
        """
        return self.get_file("root")

    def list_files(self,
                   name_equals: Optional[str] = None,
                   name_contains: Optional[str] = None,
                   mimetype: Optional[str] = None,
                   parents_in=None,
                   n=100):
        """
        Outputs the names and IDs for up to N files.
        :param name_equals:
        :param name_contains:
        :param mimetype:
        :param parents_in:
        :param n:
        :return:
        """

        query_clauses = [("trashed", "=", False)]

        if name_equals:
            query_clauses.append(("name", "=", name_equals))
        if name_contains:
            query_clauses.append(("name", "contains", name_contains))
        if mimetype:
            query_clauses.append(("mimeType", "=", mimetype))
        if parents_in:
            query_clauses.append(("parents", "in", parents_in))

        q = self._make_querystring(query_clauses)

        return self._execute_file_request(self._files.list(q=q, pageSize=n))

    def update_file(self, file_id: str,
                    remove_parents_ids=None,
                    add_parents_ids=None,
                    name: Optional[str] = None,
                    media=None):
        """

        :param file_id:
        :param remove_parents_ids:
        :param add_parents_ids:
        :param name:
        :param media:
        :return:
        """
        kw = dict(fileId=file_id)
        if remove_parents_ids:
            kw["removeParents"] = ",".join(remove_parents_ids)
        if add_parents_ids:
            kw["addParents"] = ",".join(add_parents_ids)
        if name:
            kw["body"] = {"name": name}

        if media:
            kw["media_body"] = media

        if len(kw) == 1:  # No modification, only fileId
            return

        return self._execute_file_request(self._files.update(**kw))

    def move_file_to_folder(self, file_id: str, folder_id: str):
        """

        :param file_id:
        :param folder_id:
        :return:
        """
        # Retrieve the existing parents to remove
        resp = self._files.get(fileId=file_id, fields='parents').execute()

        return self.update_file(file_id, add_parents_ids=[folder_id], remove_parents_ids=resp["parents"])

    def rename_file(self, file_id: str, name: str):
        """

        :param file_id:
        :param name:
        :return:
        """
        return self.update_file(file_id, name=name)

    def download(self, file_id: str, writer, mime_type: Optional[str] = None) -> None:
        """
        Download a file and write its content using the binary writer ``writer``.

        Example:

            with open("my_file.ext", "wb") as f:
                client.download(file_id, f)

        :param file_id:
        :param writer: binary writer
        :param mime_type:
        :return:
        """
        kw = dict(fileId=file_id)
        fn = self._files.get_media

        if mime_type:
            kw["mimeType"] = mime_type
            fn = self._files.export_media

        downloader = MediaIoBaseDownload(writer, fn(**kw))
        # bypass the downloader; there appear to be a bug for large files
        writer.write(downloader._request.execute())

    def download_file(self, file_id: str, path: str, mime_type: Optional[str] = None) -> None:
        """
        Download a file.
        :param file_id:
        :param path: local path where to save the file.
        :param mime_type:
        :return:
        """
        with open(path, "wb") as f:
            self.download(file_id, f, mime_type=mime_type)

    def download_excel_workbook(self, file_id: str) -> openpyxl.Workbook:
        """
        Download a Google Spreadsheet as an openpyxl workbook.
        :param file_id:
        :return: ``openpyxl.Workbook`` object.
        """
        buff = io.BytesIO()
        self.download(file_id, buff, mimetypes.XLSX)
        buff.seek(0)
        return openpyxl.load_workbook(buff, read_only=True)

    def upload(self, parent_id: str, name: str,
               reader,
               mime_type: Optional[str] = None,
               original_mime_type: Optional[str] = None,
               update_existing=False,
               resumable=False):
        """

        :param parent_id:
        :param name: remote filename
        :param reader: binary file reader
        :param mime_type:
        :param original_mime_type:
        :param update_existing:
        :param resumable:
        :return:
        """

        if isinstance(parent_id, File):
            parent_id = parent_id.id

        if not original_mime_type:
            import magic
            pos = reader.tell()
            buff = reader.read(1024)
            reader.seek(pos)
            original_mime_type = magic.from_buffer(buff, mime=True)

        media = MediaIoBaseUpload(reader, mimetype=original_mime_type,
                                  chunksize=CHUNKSIZE,
                                  resumable=resumable)

        if update_existing:
            f = self.file_exists(name=name, parent_id=parent_id)
            if f:
                return self.update_file(f.id, media=media)

        metadata = {
            'name': name,
            'parents': [parent_id],
        }

        if mime_type:
            metadata['mimeType'] = mime_type

        return self._execute_file_request(self._files.create(body=metadata,
                                                             media_body=media))

    def upload_file(self, parent_id: str, path: str,
                    name: Optional[str] = None,
                    mime_type: Optional[str] = None,
                    original_mime_type: Optional[str] = None,
                    update_existing=False):
        """

        :param parent_id:
        :param path: local path
        :param name: remote filename. If ``None``, use the local basename.
        :param mime_type:
        :param original_mime_type:
        :param update_existing:
        :return:
        """
        if isinstance(parent_id, File):
            parent_id = parent_id.id

        if name is None:
            name = os.path.basename(path)

        with open(path, "rb") as f:
            return self.upload(parent_id, name, f, mime_type,
                               original_mime_type,
                               update_existing=update_existing)

    def upload_excel_workbook(self,
                              parent: str,
                              name: str,
                              workbook: openpyxl.Workbook,
                              as_spreadsheet=True,
                              update_existing=False):
        """
        Upload an openpyxl (Excel) workbook and convert it to a Google Spreadsheet, unless ``as_spreadsheet`` is false.

        :param parent: parent id
        :param name: remote filename
        :param workbook: ``openpyxl.Workbook`` object
        :param as_spreadsheet: if ``True`` (default), convert the document to a Google Spreadsheet
        :param update_existing:
        :return:
        """
        buff = io.BytesIO()
        workbook.save(buff)
        buff.seek(0)

        target_mimetype = mimetypes.GOOGLE_SHEETS if as_spreadsheet else None

        return self.upload(parent, name, buff, target_mimetype,
                           mimetypes.XLSX, update_existing=update_existing)

    # Private API

    def _execute_file_request(self, req):
        """

        :param req:
        :return:
        """
        if not req.resumable:
            resp = req.execute()
            if "files" in resp:
                return [File(f, client=self) for f in resp["files"]]
            if "file" in resp:
                return File(resp["file"], client=self)
            return File(resp, client=self)
        else:
            progressless_iters = 0
            response = None
            progress = None
            while response is None:
                error = None
                try:
                    progress, response = req.next_chunk()
                    if progress:
                        print_with_carriage_return('Upload %d%%' %
                                                   (100 * progress.progress()))
                except HttpError as err:
                    error = err
                    if err.resp.status < 500:
                        raise
                except RETRYABLE_ERRORS as err:
                    error = err

                if error:
                    progressless_iters += 1
                    handle_progressless_iter(error, progressless_iters)
                else:
                    progressless_iters = 0

            if progress:
                print_with_carriage_return('Upload %d%%' %
                                           (100 * progress.progress()))

    def _make_querystring(self, clauses: List[Tuple[str, str, Any]], join="and"):
        """
        Make a "and" query string by combining all clauses. Each clause is a
        3-elements tuple of ``(field, operator, value)``. Refer to the
        following link for more information:
            https://developers.google.com/drive/v3/web/search-parameters
        :param clauses:
        :param join:
        :return:
        """
        parts = []
        for field, op, value in clauses:
            parts.append(self._make_query_clause(field, op, value))

        return (" %s " % join).join(parts)

    def _make_query_clause(self, field: str, op: str, value: Any, negation=False) -> str:
        """

        :param field:
        :param op:
        :param value:
        :param negation:
        :return:
        """
        svalue = self._serialize_query_value(value)
        if op == "in":
            p = "%s %s %s" % (svalue, op, field)
        else:
            p = "%s %s %s" % (field, op, svalue)
        if negation:
            p = "not %s" % p
        return p

    def _serialize_query_value(self, value: Any) -> str:
        """
        Serialize a query value.
        :param value:
        :return:
        """
        if isinstance(value, bool):
            return "true" if value else "false"

        return "'%s'" % str(value).replace("\\", "\\\\").replace("'", "\\'")
