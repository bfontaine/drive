# -*- coding: UTF-8 -*-

import unittest
import drive as d


class TestVersion(unittest.TestCase):
    def test_version(self):
        self.assertRegex(d.__version__, r"^\d+\.\d+\.\d+")
