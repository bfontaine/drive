# -*- coding: UTF-8 -*-

import io
import os.path
import random
import sys
import time

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
    sys.stdout.write('\r' + s)
    sys.stdout.flush()


class Client:
    """
    Google Drive client
    """

    def __init__(self, credentials_path=None):
        credentials = get_credentials(credentials_path)
        http = authorize(credentials)
        self.service = discovery.build('drive', 'v3', http=http)

    @property
    def _files(self):
        return self.service.files()


    def create_folder(self, name, parent_id):
        file_metadata = {
            "name" : name,
            "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER,
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        return self._execute_file_request(self._files.create(body=file_metadata))

    def get_or_create_folder(self, folder_name, parent_id=None):
        """ Get the ID for the folder with name folder_name."""

        folder_list = self.list_files(name_equals=folder_name,
                                      mimetype=mimetypes.GOOGLE_DRIVE_FOLDER,
                                      parents_in=parent_id,
                                      n=1)
        if folder_list:
            if len(folder_list) == 1:
                return File(folder_list[0], client=self)

            raise NameError("Unable to find folder %s" % folder_name)

        return self.create_folder(folder_name, parent_id)


    def remove_file(self, file_id):
        return self._files.delete(fileId=file_id).execute()


    def get_file_metadata(self, file_id, raise_if_not_found=True, **kw):
        try:
            return self._files.get(fileId=file_id, **kw).execute()
        except HttpError as e:
            if not raise_if_not_found:
                return None
            raise e


    def get_file(self, file_id, raise_if_not_found=True):
        fm = self.get_file_metadata(file_id, raise_if_not_found)
        if fm:
            return File(fm, client=self)


    def get_file_by_name(self, name, parent_id=None):
        kw = dict(name_equals=name, n=1)
        if parent_id:
            kw["parents_in"] = parent_id
        ls = self.list_files(**kw)
        if not ls:
            raise FileNotFoundException(name)

        return ls[0]


    def file_exists(self, name=None, file_id=None, parent_id=None):
        """
        Check if a file exists and if so returns it.
        """
        if not name and not file_id:
            raise RuntimeError("You must provide a name or file_id")

        if file_id:
            return bool(self.get_file(file_id, raise_if_not_found=False))

        files = self.list_files(name_equals=name, parents_in=parent_id, n=1)
        if not files:
            return False
        return files[0]


    def files_shared_with_me(self):
        return self._execute_file_request(self._files.list(q="sharedWithMe=true"))


    def get_shared_file(self, name, is_directory=None):
        """
        Retrieve a shared file. If ``is_directory`` is a boolean, it’s used to
        filter files that are (or not) directories. By default the first
        matching file is returned without checking if it’s a directory or not.
        """
        for shared in self.files_shared_with_me():
            if shared.name == name:
                if is_directory is False and shared.is_directory:
                    continue
                if is_directory and not shared.is_directory:
                    continue

                return shared
        raise FileNotFoundException(name)


    def get_shared_directory(self, name):
        """
        Retrieve a shared directory. This is a shortcut for
        ``get_shared_file(name, is_directory=True)``.
        """
        return self.get_shared_file(name, is_directory=True)


    def root(self):
        return self.get_file("root")


    def list_files(self, name_equals=None, name_contains=None,
                        mimetype=None, parents_in=None,
                        n=100):
        """Outputs the names and IDs for up to N files."""

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

    def update_file(self, file_id, remove_parents_ids=None,
                                   add_parents_ids=None,
                                   name=None, media=None):
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

    def move_file_to_folder(self, file_id, folder_id):
        # Retrieve the existing parents to remove
        resp = self._files.get(fileId=file_id, fields='parents').execute();

        return self.update_file(file_id, add_parents_ids=[folder_id],
                                         remove_parents_ids=resp["parents"])

    def rename_file(self, file_id, name):
        return self.update_file(file_id, name=name)


    def download(self, file_id, binwriter, mime_type=None):
        """ Download a file and write its content using ``binwriter``."""
        kw = dict(fileId=file_id)
        fn = self._files.get_media

        if mime_type:
            kw["mimeType"] = mime_type
            fn = self._files.export_media

        downloader = MediaIoBaseDownload(binwriter, fn(**kw))
        # bypass the downloader; there appear to be a bug for large files
        binwriter.write(downloader._request.execute())


    def download_file(self, file_id, path, mime_type=None):
        with open(path, "wb") as f:
            self.download(file_id, f, mime_type=mime_type)


    def download_excel_workbook(self, file_id):
        """ Download a Google Spreadsheet as an openpyxl workbook """
        buff = io.BytesIO()
        self.download(file_id, buff, mimetypes.XLSX)
        buff.seek(0)
        return openpyxl.load_workbook(buff, read_only=True)

    def upload(self, parent_id, name, binreader, 
               mime_type=None, original_mime_type=None,
               update_existing=False,
               resumable=False):

        if isinstance(parent_id, File):
            parent_id = parent_id.id

        if not original_mime_type:
            import magic
            pos = binreader.tell()
            buff = binreader.read(1024)
            binreader.seek(pos)
            original_mime_type = magic.from_buffer(buff, mime=True)

        media = MediaIoBaseUpload(binreader, mimetype=original_mime_type,
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





    def upload_file(self, parent_id, path, name=None, mime_type=None,
                                                      original_mime_type=None,
                                                      update_existing=False):
        if isinstance(parent_id, File):
            parent_id = parent_id.id

        if name is None:
            name = os.path.basename(path)

        with open(path, "rb") as f:
            return self.upload(parent_id, name, f, mime_type,
                               original_mime_type,
                               update_existing=update_existing)


    def upload_excel_workbook(self, parent, name, workbook,
                                                  as_spreadsheet=True,
                                                  update_existing=False):
        """
        Upload an openpyxl (Excel) workbook and convert it to a Google
        Spreadsheet unless ``as_spreadsheet`` is false.
        """
        buff = io.BytesIO()
        workbook.save(buff)
        buff.seek(0)

        target_mimetype = mimetypes.GOOGLE_SHEETS if as_spreadsheet else None

        return self.upload(parent, name, buff, target_mimetype,
                           mimetypes.XLSX, update_existing=update_existing)

    # Private API

    def _execute_file_request(self, req):
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

    def _make_querystring(self, clauses, join="and"):
        """
        Make a "and" query string by combining all clauses. Each clause is a
        3-elements tuple of ``(field, operator, value)``. Refer to the
        following link for more information:
            https://developers.google.com/drive/v3/web/search-parameters
        """
        parts = []
        for field, op, value in clauses:
            parts.append(self._make_query_clause(field, op, value))

        return (" %s " % join).join(parts)


    def _make_query_clause(self, field, op, value, negation=False):
        svalue = self._serialize_query_value(value)
        if op == "in":
            p = "%s %s %s" % (svalue, op, field)
        else:
            p = "%s %s %s" % (field, op, svalue)
        if negation:
            p = "not %s" % p
        return p


    def _serialize_query_value(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"

        return "'%s'" % str(value).replace("\\", "\\\\").replace("'", "\\'")
