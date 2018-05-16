#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""

import datetime
import unittest
from unittest.mock import patch

from tools import helpers


class ToolsHelpersTestCase(unittest.TestCase):
    """Tools Helpers Test Cases."""

    def setUp(self):
        """Set up tests."""
        pass

    @patch('tools.helpers.compute_utc_offset')
    def test_newtime(self, offset):
        """Conversion from local to UTC."""
        offset.return_value = datetime.timedelta(-1, 54000)
        expected = '2018-05-11T01:11:08Z'
        actual = helpers.newtime('2018-05-11T10:11:08')
        self.assertEqual(expected, actual)



if __name__ == '__main__':
    unittest.main()
