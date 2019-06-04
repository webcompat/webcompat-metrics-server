#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Web views on Webcompat Metrics Server."""
import unittest

from ochazuke import create_app


class WebTestCase(unittest.TestCase):
    """General Test Cases for views."""

    def setUp(self):
        """Set up tests."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_index(self):
        """Test the index page."""
        rv = self.client.get('/')
        self.assertIn('Welcome to ochazuke', rv.data.decode())


if __name__ == '__main__':
    unittest.main()
