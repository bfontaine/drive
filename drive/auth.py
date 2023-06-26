# -*- coding: UTF-8 -*-

import os
import httplib2
from os import environ
from typing import Optional

from oauth2client.service_account import ServiceAccountCredentials  # type: ignore

from drive.exceptions import DriveException

ENV_CLIENT_SECRET_PATH = "GOOGLE_APPLICATION_CREDENTIALS"

# If you modify these scopes, delete your previously-saved credentials
DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'


class MissingCredentialsException(DriveException):
    def __init__(self):
        super().__init__("Missing credentials! Please set %s" % ENV_CLIENT_SECRET_PATH)


def get_credentials(path: Optional[str] = None):
    """
    Retrieve the user's Google Cloud credentials.
    """

    if path is None:
        if ENV_CLIENT_SECRET_PATH not in environ:
            raise MissingCredentialsException()

        path = environ[ENV_CLIENT_SECRET_PATH]

    path = os.path.expanduser(path)
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scopes=[DRIVE_SCOPE])
    if not creds or creds.invalid:
        raise MissingCredentialsException()
    return creds


def authorize(credentials):
    return credentials.authorize(httplib2.Http())


def authorize_credentials(credentials_path: Optional[str] = None):
    """Equivalent of authorize(get_credentials(credentials_path))."""
    return authorize(get_credentials(credentials_path))
