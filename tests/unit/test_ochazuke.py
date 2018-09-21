#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Main testing module for Webcompat Metrics Server."""
import json
import unittest
from unittest.mock import patch

from werkzeug.datastructures import ImmutableMultiDict

from ochazuke import create_app
from ochazuke import helpers


TIMELINE = {'about': 'Hourly NeedsDiagnosis issues count',
            'date_format': 'w3c',
            'timeline': []
            }

DATA = [{"count": "485", "timestamp": "2018-05-15T01:00:00Z"},
        {"count": "485", "timestamp": "2018-05-16T02:00:00Z"},
        {"count": "485", "timestamp": "2018-05-17T03:00:00Z"},
        {"count": "485", "timestamp": "2018-05-18T04:00:00Z"},
        ]

WEEKLY_DATA = {
    "2015": [9, 7, 46],
    "2016": [11, 19, 28],
    "2017": [35, 29, 40]
}


def mocked_json(expected_data):
    """Prepare a json response when fed a dictionary."""
    return json.dumps(expected_data)


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

    @patch('ochazuke.get_remote_data')
    def test_needsdiagnosis(self, mock_get):
        """/data/needsdiagnosis-timeline sends back JSON."""
        TIMELINE['timeline'] = DATA
        mock_get.return_value = mocked_json(TIMELINE)
        rv = self.client.get('/data/needsdiagnosis-timeline')
        self.assertIn(
            '"about": "Hourly NeedsDiagnosis issues count"',
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

    @patch('ochazuke.get_weekly_data')
    def test_weeklydata(self, mock_get):
        """/data/weekly-counts sends back JSON."""
        mock_get.return_value = mocked_json(WEEKLY_DATA)
        rv = self.client.get('/data/weekly-counts')
        self.assertIn('"2016": [11, 19, 28]', rv.data.decode())
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

    @patch('ochazuke.get_remote_data')
    def test_needsdiagnosis_valid_param(self, mock_get):
        """valid parameters on /needsdiagnosis-timeline."""
        TIMELINE['timeline'] = DATA
        mock_get.return_value = mocked_json(TIMELINE)
        url = '/data/needsdiagnosis-timeline?from=2018-05-16&to=2018-05-18'
        rv = self.client.get(url)
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-17T03:00:00Z"}',
            rv.data.decode())
        self.assertNotIn(
            '{"count": "485", "timestamp": "2018-05-15T01:00:00Z"}',
            rv.data.decode())

    @patch('ochazuke.get_remote_data')
    def test_needsdiagnosis_invalid_param(self, mock_get):
        """Ignore invalid parameters on /needsdiagnosis-timeline."""
        TIMELINE['timeline'] = DATA
        mock_get.return_value = mocked_json(TIMELINE)
        rv = self.client.get('/data/needsdiagnosis-timeline?blah=foo')
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-15T01:00:00Z"}',
            rv.data.decode())
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-18T04:00:00Z"}',
            rv.data.decode())

    @patch('ochazuke.get_remote_data')
    def test_needsdiagnosis_invalid_param_values(self, mock_get):
        """Ignore invalid parameters values on /needsdiagnosis-timeline."""
        TIMELINE['timeline'] = DATA
        mock_get.return_value = mocked_json(TIMELINE)
        rv = self.client.get('/data/needsdiagnosis-timeline?from=foo&to=bar')
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-15T01:00:00Z"}',
            rv.data.decode())
        self.assertIn(
            '{"count": "485", "timestamp": "2018-05-18T04:00:00Z"}',
            rv.data.decode())

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

    def test_get_timeline_slice(self):
        """Given a list of dates, return the appropriate slice of data."""
        dates = ['2018-05-16', '2018-05-17']
        sliced = [
            {"count": "485", "timestamp": "2018-05-16T02:00:00Z"},
            {"count": "485", "timestamp": "2018-05-17T03:00:00Z"}
            ]
        self.assertEqual(helpers.get_timeline_slice(DATA, dates), sliced)

    def test_get_timeline_slice_out_of_range(self):
        """Empty list if the dates list and the timeline do not match."""
        dates = ['2018-04-16']
        full_list = [
            {"count": "485", "timestamp": "2018-05-15T01:00:00Z"},
            {"count": "485", "timestamp": "2018-05-16T02:00:00Z"},
            ]
        self.assertEqual(helpers.get_timeline_slice(full_list, dates), [])

    def test_is_valid_args(self):
        """Return True or False depending on the args"""
        self.assertTrue(helpers.is_valid_args(
            ImmutableMultiDict([('from', '2018-05-16'), ('to', '2018-05-18')]))
            )
        self.assertFalse(helpers.is_valid_args(ImmutableMultiDict([])))
        self.assertFalse(helpers.is_valid_args(
            ImmutableMultiDict([('bar', 'foo')]))
            )
        self.assertFalse(helpers.is_valid_args(
            ImmutableMultiDict([('from', 'bar'), ('to', 'foo')]))
            )


if __name__ == '__main__':
    unittest.main()
