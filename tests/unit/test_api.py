#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""
import json
import os
import unittest
from unittest.mock import patch

from ochazuke import create_app
from ochazuke import db


DATA = [{"count": "485", "timestamp": "2018-05-16T02:00:00Z"},
        {"count": "485", "timestamp": "2018-05-17T03:00:00Z"},
        {"count": "485", "timestamp": "2018-05-18T04:00:00Z"},
        ]

WEEKLY_DATA = [{"count": 471, "timestamp": "2019-05-20T00:00:00Z"},
               {"count": 392, "timestamp": "2019-05-27T00:00:00Z"},
               {"count": 407, "timestamp": "2019-06-03T00:00:00Z"}
               ]


def json_data(filename):
    """Return a tuple with the content and its signature."""
    current_root = os.path.realpath(os.curdir)
    fixtures_path = 'tests/fixtures'
    path = os.path.join(current_root, fixtures_path, filename)
    with open(path, 'r') as f:
        json_event = json.dumps(json.load(f))
    return json_event


class APITestCase(unittest.TestCase):
    """General Test Cases for views."""

    def setUp(self):
        """Set up tests."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        # Initialize a DB?
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('ochazuke.api.views.get_weekly_data')
    def test_weeklydata(self, mock_get):
        """Send back on /data/weekly-counts a JSON."""
        mock_get.return_value = WEEKLY_DATA
        rv = self.client.get(
            '/data/weekly-counts?from=2019-05-16&to=2019-06-04')
        self.assertIn(
            (
                '{"count": 392, "timestamp": "2019-05-27T00:00:00Z"}'
            ), rv.data.decode())
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/json')
        self.assertTrue('Access-Control-Allow-Origin' in rv.headers.keys())
        self.assertEqual('*', rv.headers['Access-Control-Allow-Origin'])
        self.assertTrue('Vary' in rv.headers.keys())
        self.assertEqual('Origin', rv.headers['Vary'])
        self.assertTrue(
            'Access-Control-Allow-Credentials' in rv.headers.keys())
        self.assertEqual('true',
                         rv.headers['Access-Control-Allow-Credentials'])

    @patch('ochazuke.api.views.get_timeline_data')
    def test_needsdiagnosis_valid_param(self, mock_timeline):
        """Valid parameters on /needsdiagnosis-timeline."""
        mock_timeline.return_value = DATA
        url = '/data/needsdiagnosis-timeline?from=2018-05-16&to=2018-05-18'
        rv = self.client.get(url)
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-17T03:00:00Z"}',
            rv.data.decode())
        self.assertIn(
            '"about": "Hourly needsdiagnosis issues count"',
            rv.data.decode())
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/json')
        self.assertTrue('Access-Control-Allow-Origin' in rv.headers.keys())
        self.assertEqual('*', rv.headers['Access-Control-Allow-Origin'])
        self.assertTrue('Vary' in rv.headers.keys())
        self.assertEqual('Origin', rv.headers['Vary'])
        self.assertTrue(
            'Access-Control-Allow-Credentials' in rv.headers.keys())
        self.assertEqual('true',
                         rv.headers['Access-Control-Allow-Credentials'])

    @patch('ochazuke.api.views.get_remote_data')
    def test_triage_stats(self, mock_get):
        """/data/triage-bugs sends back JSON."""
        mock_get.return_value = json_data('triage.json')
        rv = self.client.get('/data/triage-bugs')
        self.assertIn(
            '"title": "example.org - dashboard test"',
            rv.data.decode())
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/json')
        self.assertTrue('Access-Control-Allow-Origin' in rv.headers.keys())
        self.assertEqual('*', rv.headers['Access-Control-Allow-Origin'])
        self.assertTrue('Vary' in rv.headers.keys())
        self.assertEqual('Origin', rv.headers['Vary'])
        self.assertTrue(
            'Access-Control-Allow-Credentials' in rv.headers.keys())
        self.assertEqual('true',
                         rv.headers['Access-Control-Allow-Credentials'])

    def test_needsdiagnosis_without_params(self):
        """/data/needsdiagnosis-timeline without params fail."""
        rv = self.client.get('/data/needsdiagnosis-timeline')
        self.assertEqual(rv.status_code, 404)

    def test_needsdiagnosis_invalid_param(self):
        """Ignore invalid parameters on /needsdiagnosis-timeline."""
        rv = self.client.get('/data/needsdiagnosis-timeline?blah=foo')
        self.assertEqual(rv.status_code, 404)

    def test_needsdiagnosis_invalid_param_values(self):
        """Ignore invalid parameters values on /needsdiagnosis-timeline."""
        rv = self.client.get('/data/needsdiagnosis-timeline?from=foo&to=bar')
        self.assertEqual(rv.status_code, 404)


if __name__ == '__main__':
    unittest.main()
