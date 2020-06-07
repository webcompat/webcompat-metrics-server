#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""
import unittest

from tools import helpers


class ToolsHelpersTestCase(unittest.TestCase):
    """General Test Cases for global helpers."""

    def test_url_with_params(self):
        """Given a dict of parameters and a URL, returns an encoded URL."""
        url = "https://example.com/test"
        parameters = {
            "test": "example",
            "hello=world": "this/needs/encoding"
        }
        expected = "https://example.com/test?test=example&hello%3Dworld=this%2Fneeds%2Fencoding" # noqa

        self.assertEqual(helpers.url_with_params(url, parameters), expected)


if __name__ == '__main__':
    unittest.main()
