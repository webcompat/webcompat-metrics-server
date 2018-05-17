#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""
import unittest

from ochazuke import create_app


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


if __name__ == '__main__':
    unittest.main()
