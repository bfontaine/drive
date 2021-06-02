# -*- coding: UTF-8 -*-

import unittest
from drive.files import File
from drive import mimetypes


class TestFiles(unittest.TestCase):
    def test_name(self):
        name = "Foo Bar"
        file = File({"id": "xx", "name": name})
        self.assertEqual(name, file.name)

    def test_is_directory(self):
        self.assertIsNone(File({"id": "xx"}).is_directory)
        self.assertFalse(File({"id": "xx", "mimeType": "something"}).is_directory)
        self.assertFalse(File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FILE}).is_directory)
        self.assertTrue(File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}).is_directory)

    def test_human_type(self):
        self.assertEqual("?", File({"id": "xx"}).human_type)
        self.assertEqual("?", File({"id": "xx", "name": "foo.json"}).human_type)
        self.assertEqual("JSONS", File({"id": "xx", "name": "foo.jsons"}).human_type)
        self.assertEqual("JSON", File({"id": "xx", "name": "foo.jsons", "mimeType": mimetypes.JSON}).human_type)
        self.assertEqual("folder", File({"id": "xx", "mimeType": mimetypes.GOOGLE_DRIVE_FOLDER}).human_type)

    def test_exists(self):
        self.assertIsNone(File({"id": "xx"}).exists())
