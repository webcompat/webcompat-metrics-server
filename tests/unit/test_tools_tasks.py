#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""

import unittest
from unittest.mock import mock_open
from unittest.mock import patch

from tools import jobs_tasks


class ToolsTasksTestCase(unittest.TestCase):
    """Tasks Test Cases in tools."""

    def setUp(self):
        """Set up tests."""
        pass

    def test_get_last_total(self):
        """Grab the last timestamp and its total."""
        with patch('tools.jobs_tasks.open',
                   mock_open(read_data='2001-01-01T10:20:30Z 123'),
                   create=True):
            actual = jobs_tasks.get_last_total('needsdiagnosis')
            self.assertIs(type(actual), int)
            self.assertEqual(actual, 123)
        with patch('tools.jobs_tasks.open',
                   mock_open(read_data=''),
                   create=True):
            actual = jobs_tasks.get_last_total('needsdiagnosis')
            self.assertIsNone(actual)
        with patch('tools.jobs_tasks.open',
                   mock_open(read_data=' '),
                   create=True):
            actual = jobs_tasks.get_last_total('needsdiagnosis')
            self.assertIsNone(actual)

    def test_update_timeline(self):
        """Run the tasks for updating the data-timeline"""
        self.assertFalse(jobs_tasks.update_timeline('punkcat'))

    def test_get_live_total(self):
        """Extract the live total from GitHub."""
        self.assertFalse(jobs_tasks.get_live_total('punkcat'))
        with patch('tools.jobs_tasks.get_remote_data') as mock_remote:
            mock_remote.return_value = b'{"open_issues": 123}'
            actual = jobs_tasks.get_live_total('needsdiagnosis')
            self.assertIs(type(actual), int)
            self.assertEqual(actual, 123)


if __name__ == '__main__':
    unittest.main()
