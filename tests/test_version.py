# -*- coding: UTF-8 -*-
import re

import drive as d


def test_version():
    assert re.match(r"^\d+\.\d+\.\d+", d.__version__)
