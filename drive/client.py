# -*- coding: UTF-8 -*-

import io
import os.path
import random
import sys
import time
from typing import Optional, List, Any, Tuple, Dict, cast, Iterable, Union

import httplib2
import openpyxl
from apiclient import discovery  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload  # type: ignore

from drive import mimetypes
from drive.auth import authorize_credentials
from drive.exceptions import FileNotFoundException
from drive.files import File, guess_original_mime_type

# Retry transport and file IO errors.
RETRYABLE_ERRORS = (httplib2.HttpLib2Error, IOError)
# Default number of bytes to send/receive in each request.
CHUNKSIZE = 2 * 1024 * 1024

QueryClause = Tuple[str, str, Any]


def handle_progressless_iter(error, progressless_iters, *, retries_count=5):
    if progressless_iters > retries_count:
        print('Failed to make progress for too many consecutive iterations.')
        raise error

    sleep_time = random.random() * (2 ** progressless_iters)
    # TODO: use a logger
    print('Caught exception (%s). Sleeping for %s seconds before retry #%d.'
          % (str(error), sleep_time, progressless_iters))
    time.sleep(sleep_time)


def print_with_carriage_return(s):
    """
    Internal utility to print a one-line string prefixed with a carriage return (``\\r``).
    :param s: string to print
    :return: None
    """
    sys.stdout.write('\r' + s)
    sys.stdout.flush()


def _make_querystring(clauses: Iterable[QueryClause], join="and"):
    """
    Make an "and" query string by combining all clauses.
    Each clause is a 3-elements tuple of ``(field, operator, value)``.
    Refer to the following link for more information:
        https://developers.google.com/drive/v3/web/search-parameters
    """
    parts = []
    for field, op, value in clauses:
        parts.append(_make_query_clause(field, op, value))

    return (" %s " % join).join(parts)


def _make_query_clause(field: str, op: str, value, negation=False) -> str:
    serialized_value = _serialize_query_value(value)
    if op == "in":
        p = "%s %s %s" % (serialized_value, op, field)
    else:
        p = "%s %s %s" % (field, op, serialized_value)
    if negation:
        p = "not %s" % p
    return p


def _resolve_parent_id(parent: Union[File, str]):
    if isinstance(parent, File):
        return parent.id
    return parent


def _serialize_query_value(value):
    """
    Serialize a query value.
    """
    if isinstance(value, bool):
        return "true" if value else "false"

    return "'%s'" % str(value).replace("\\", "\\\\").replace("'", "\\'")


class Client:
    """Google Drive client"""

    def __init__(self, credentials_path: Optional[str] = None, *, download_retries_count=5):
        http = authorize_credentials(credentials_path)
        self.service = discovery.build('drive', 'v3', http=http)
        self.download_retries_count = download_retries_count

    @property
    def _files(self):
        return self.service.files()

    @property
    def _permissions(self):
        return self.service.permissions()

    def create_folder(self, name: str, parent_id: Optional[str] = None):
        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER,
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        return self._execute_file_request(self._files.create(body=file_metadata))

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None):
        """
        Get the ID for the folder with name folder_name, creating it if it doesn't exist.
        """

        folder_list = self.list_files(name_equals=folder_name,
                                      mimetype=mimetypes.GOOGLE_DRIVE_FOLDER,
                                      parents_in=parent_id,
                                      n=1)
        if folder_list:
            if len(folder_list) == 1:
                return File(folder_list[0], client=self)

            raise RuntimeError("Unable to find folder %s" % folder_name)

        return self.create_folder(folder_name, parent_id)

    def remove_file(self, file_id: str):
        """
        Remove a file by its ID.
        """
        return self._files.delete(fileId=file_id).execute()

    def get_file_metadata(self, file_id, raise_if_not_found=True, **kw):
        try:
            return self._files.get(fileId=file_id, **kw).execute()
        except HttpError:
            if not raise_if_not_found:
                return None
            raise

    def get_file(self, file_id: str, raise_if_not_found=True) -> Optional[File]:
        """
        Get a file by its ID.

        :param file_id:
        :param raise_if_not_found: if ``True`` (default), raise an exception if the file doesn’t exist
        """
        fm = self.get_file_metadata(file_id, raise_if_not_found)
        if fm:
            return File(fm, client=self)
        return None

    def get_file_by_name(self, name: str, parent_id: Optional[str] = None) -> Optional[File]:
        """
        Get a file by name.
        Note that, unlike IDs, names are not guaranteed to be unique: you can have multiple files with the same name
        on Google Drive.

        :param name: Drive filename
        :param parent_id: optional parent ID.
        :raise: ``drive.exceptions.FileNotFoundException`` if the file doesn’t exist
        """
        ls = self.list_files(name_equals=name, n=1, parents_in=parent_id)
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
            return None
        return files[0]

    def files_shared_with_me(self) -> List[File]:
        """
        Return a list of files (and 'directories') 'shared with me'.
        """
        return self._execute_file_request(self._files.list(q="sharedWithMe=true"))

    def get_shared_file(self, name: str,
                        is_directory: Optional[bool] = None,
                        raise_if_not_found=True) -> Optional[File]:
        """
        Retrieve a shared file.
        If ``is_directory`` is a boolean, it’s used to filter files that are (or not) directories. By default, the first
        matching file is returned without checking if it’s a directory or not.
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

        return None

    def get_shared_directory(self, name: str) -> Optional[File]:
        """
        Retrieve a shared directory. This is a shortcut for ``get_shared_file(name, is_directory=True)``.
        """
        return self.get_shared_file(name, is_directory=True)

    def root(self) -> File:
        """
        Return the root directory. Note the alias ``"root"`` works as an alias file ID for the root directory.
        """
        return cast(File, self.get_file("root"))

    def list_files(self,
                   name_equals: Optional[str] = None,
                   name_contains: Optional[str] = None,
                   mimetype: Optional[str] = None,
                   parents_in: Optional[str] = None,
                   n=100):
        """
        Return the names and IDs for up to N files.
        """

        query_clauses: List[QueryClause] = [("trashed", "=", False)]

        if name_equals:
            query_clauses.append(("name", "=", name_equals))
        if name_contains:
            query_clauses.append(("name", "contains", name_contains))
        if mimetype:
            query_clauses.append(("mimeType", "=", mimetype))
        if parents_in:
            query_clauses.append(("parents", "in", parents_in))

        q = _make_querystring(query_clauses)

        return self._execute_file_request(self._files.list(q=q, pageSize=n))

    def update_file(self, file_id: str,
                    remove_parents_ids=None,
                    add_parents_ids=None,
                    name: Optional[str] = None,
                    media=None,
                    force=False):
        """
        Update a file.

        Note: calling this function with only a file ID (e.g.: `update_file(my_id)`) without any modification is a no-op
          unless `force=True` is passed.

        :param file_id: ID of the file to update
        :param remove_parents_ids:
        :param add_parents_ids:
        :param name: new name of the file
        :param media:
        :param force: force update even if there are no modifications
        :return:
        """
        modified = force or remove_parents_ids or add_parents_ids or name or media
        if not modified:
            return

        kw: Dict[str, Any] = {}

        if remove_parents_ids:
            kw["removeParents"] = ",".join(remove_parents_ids)

        if add_parents_ids:
            kw["addParents"] = ",".join(add_parents_ids)

        if name:
            kw["body"] = {"name": name}

        if media:
            kw["media_body"] = media

        return self._execute_file_request(self._files.update(fileId=file_id, **kw))

    def move_file_to_folder(self, file_id: str, folder_id: str):
        # Retrieve the existing parents to remove
        parent_ids = self._get_file_field(file_id, "parents")
        return self.update_file(file_id, add_parents_ids=[folder_id], remove_parents_ids=parent_ids)

    def rename_file(self, file_id: str, name: str):
        """
        Rename a file.
        """
        return self.update_file(file_id, name=name)

    def download(self, file_id: str, writer, mime_type: Optional[str] = None) -> None:
        """
        Download a file and write its content using the binary writer ``writer``. See also ``download_file``.

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
        # noinspection PyProtectedMember
        writer.write(downloader._request.execute())

    def download_file(self, file_id: str, path: str, mime_type: Optional[str] = None) -> None:
        """
        Download a file and save it locally.
        :param file_id: file ID
        :param path: local path where to save the file.
        :param mime_type: optional mime type
        :return:
        """
        with open(path, "wb") as f:
            self.download(file_id, f, mime_type=mime_type)

    def download_excel_workbook(self, file_id: str, read_only=False):
        """
        Download a Google Spreadsheet as an openpyxl workbook.

        :param file_id:
        :param read_only: set this to ``True`` if you don't plan to save or edit the workbook.
        :return: ``openpyxl.Workbook`` object.
        """
        buff = io.BytesIO()
        self.download(file_id, buff, mimetypes.XLSX)
        buff.seek(0)
        return openpyxl.load_workbook(buff, read_only=read_only)

    def upload(self, parent_id: Union[str, File], name: str,
               reader,
               mime_type: Optional[str] = None,
               original_mime_type: Optional[str] = None,
               update_existing=False,
               resumable=False):
        """
        :param parent_id:
        :param name: remote filename
        :param reader: binary file reader
        :param mime_type: target MIME type.
        :param original_mime_type: Original MIME type. If ``None``, it is determined using libmagic, which must be
            installed.
        :param update_existing:
        :param resumable:
        :return:
        """
        parent_id_str = _resolve_parent_id(parent_id)

        if not original_mime_type:
            original_mime_type = guess_original_mime_type(reader)

        media = MediaIoBaseUpload(reader, mimetype=original_mime_type,
                                  chunksize=CHUNKSIZE,
                                  resumable=resumable)

        if update_existing:
            f = self.file_exists(name=name, parent_id=parent_id_str)
            if f:
                return self.update_file(f.id, media=media)

        metadata = {
            'name': name,
            'parents': [parent_id_str],
        }

        if mime_type:
            metadata['mimeType'] = mime_type

        return self._execute_file_request(self._files.create(body=metadata,
                                                             media_body=media))

    def upload_file(self, parent_id: Union[str, File], path: str,
                    name: Optional[str] = None,
                    mime_type: Optional[str] = None,
                    original_mime_type: Optional[str] = None,
                    update_existing=False):
        """
        :param parent_id:
        :param path: local path
        :param name: remote filename. If ``None``, use the local basename.
        :param mime_type:
        :param original_mime_type: Original MIME type. If ``None``, it is determined using libmagic, which must be
            installed.
        :param update_existing:
        :return:
        """
        if name is None:
            name = os.path.basename(path)

        with open(path, "rb") as f:
            return self.upload(parent_id, name, f, mime_type,
                               original_mime_type,
                               update_existing=update_existing)

    def upload_excel_workbook(self,
                              parent: Union[str, File],
                              name: str,
                              workbook: openpyxl.Workbook,
                              as_spreadsheet=True,
                              update_existing=False):
        """
        Upload an openpyxl (Excel) workbook and convert it to a Google Spreadsheet, unless ``as_spreadsheet`` is false.

        :param parent: parent ID
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

    def grant_file_permissions(self, file_id: str, role: str, type_: str):
        return self._permissions.create(fileId=file_id, body={"role": role, "type": type_}).execute()

    def get_web_view_link(self, file_id: str) -> str:
        return self._get_file_field(file_id, "webViewLink")

    def _get_file_field(self, file_id: str, field: str):
        resp = self._files.get(fileId=file_id, fields=field).execute()
        return resp[field]

    # Private API

    def _execute_file_request(self, req):
        if not req.resumable:
            resp = req.execute()
            if "files" in resp:
                return [File(f, client=self) for f in resp["files"]]
            if "file" in resp:
                return File(resp["file"], client=self)
            return File(resp, client=self)

        progressless_iters = 0
        response = None
        progress = None
        while response is None:
            error = None
            try:
                progress, response = req.next_chunk()
                if progress:
                    print_with_carriage_return('Upload %d%%' % (100 * progress.progress()))
            except HttpError as err:
                error = err
                if err.resp.status < 500:
                    raise
            except RETRYABLE_ERRORS as err:
                error = err

            if error:
                progressless_iters += 1
                handle_progressless_iter(error, progressless_iters, retries_count=self.download_retries_count)
            else:
                progressless_iters = 0

        if progress:
            print_with_carriage_return('Upload %d%%' %
                                       (100 * progress.progress()))
