# -*- coding: UTF-8 -*-

import os
import httplib2
from os import environ
from typing import Optional

from oauth2client.service_account import ServiceAccountCredentials

from drive.exceptions import DriveException

ENV_CLIENT_SECRET_PATH = "GOOGLE_APPLICATION_CREDENTIALS"

# If you modify these scopes, delete your previously saved credentials
DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'


class MissingCredentialsException(DriveException):
    def __init__(self):
        super().__init__("Missing credentials! Please set %s" % ENV_CLIENT_SECRET_PATH)


def get_credentials(path: Optional[str] = None):
    """
    Retrieve the user's Google Cloud credentials.
    :param path:
    :return:
    """

    if path is None:
        path = environ["GOOGLE_APPLICATION_CREDENTIALS"]

    path = os.path.expanduser(path)
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scopes=[DRIVE_SCOPE])
    if not creds or creds.invalid:
        raise MissingCredentialsException()
    return creds


def authorize(credentials):
    """

    :param credentials:
    :return:
    """
    return credentials.authorize(httplib2.Http())
