#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""
import unittest

from ochazuke import create_app
from ochazuke import helpers


class OchazukeTestCase(unittest.TestCase):
    """General Test Cases for views."""

    def setUp(self):
        """Set up tests."""
        self.app = create_app(test_config={})
        self.client = self.app.test_client()

    def test_index(self):
        """Test the index page."""
        rv = self.client.get('/')
        self.assertIn('Welcome to ochazuke', rv.data.decode())

    def test_needsdiagnosis(self):
        """/needsdiagnosis-timeline sends back JSON."""
        rv = self.client.get('/data/needsdiagnosis-timeline')
        self.assertIn(
            '"about": "Hourly NeedsDiagnosis issues count"',
            rv.data.decode())
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/json')

    def test_date_range(self):
        """Given from_date and to_date, return a number of days."""
        from_date = '2018-01-02'
        to_date = '2018-01-04'
        days = ['2018-01-02', '2018-01-03']
        self.assertCountEqual(helpers.get_days(from_date, to_date), days)
        self.assertCountEqual(helpers.get_days(to_date, from_date), days)

    def test_date_range_invalid(self):
        """Given from_date and to_date, return a number of days."""
        from_date = '2018-01-02T23:00'
        to_date = '2018-01-04'
        self.assertEqual(helpers.get_days(from_date, to_date), None)

    def test_date_range_same_day(self):
        """Given from_date and to_date, return a number of days."""
        from_date = '2018-01-02'
        to_date = '2018-01-02'
        self.assertEqual(helpers.get_days(from_date, to_date), ['2018-01-02'])


if __name__ == '__main__':
    unittest.main()
