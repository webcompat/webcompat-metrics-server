#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for our webhooks."""

import json
import os
import unittest

import flask

from ochazuke import create_app
from ochazuke.models import db
from ochazuke.models import Issue
from ochazuke.models import Event
from ochazuke.webhooks import helpers


# The key is for testing and computing the signature.
# TODO: figure out storage/retrieval configuration
key = 'SECRETS'


# Some machinery for opening our test files
def event_data(filename):
    """Return a tuple with the content and its signature."""
    current_root = os.path.realpath(os.curdir)
    events_path = 'tests/fixtures/webhooks'
    path = os.path.join(current_root, events_path, filename)
    with open(path, 'r') as f:
        json_event = json.dumps(json.load(f))
    signature = 'sha1={sig}'.format(
        sig=helpers.get_payload_signature(key, json_event))
    return json_event, signature


class TestWebhooks(unittest.TestCase):
    """Tests for our webhooks handler."""

    def setUp(self):
        """Set up tests."""
        self.app = create_app(test_config={})
        self.client = self.app.test_client()
        # binds app to the current context
        self.app_context = self.app.app_context()
        # create all the tables for testing
        db.create_all()
        self.headers = {'content-type': 'application/json'}
        self.test_url = '/webhooks/issues'
        self.payload = {'issue_id': 2475,
                        'header': 'Can\'t log in to www.artisanalmustard.com!',
                        'created_at': '2018-07-30T13:22:36Z',
                        'milestone': 'needsdiagnosis',
                        'actor': 'laghee',
                        'action': 'opened',
                        'details': None,
                        'received_at': '2018-07-30T13:23:43Z'}

    def tearDown(self):
        """Tear down tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_forbidden_get(self):
        """GET is forbidden on issues webhook."""
        rv = self.app.get(self.test_url, headers=self.headers)
        self.assertEqual(rv.status_code, 404)

    def test_fail_on_missing_signature(self):
        """POST without signature on issues webhook is forbidden."""
        self.headers.update({'X-GitHub-Event': 'ping'})
        rv = self.app.post(self.test_url, headers=self.headers)
        self.assertEqual(rv.status_code, 401)
        self.assertEqual(rv.data, 'Move along, nothing to see here')
        self.assertEqual(rv.mimetype, 'text/plain')

    def test_fail_on_bogus_signature(self):
        """POST without bogus signature on issues webhook is forbidden."""
        json_event, signature = event_data('new_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'ping',
                             'X-Hub-Signature': 'Boo!'})
        rv = self.app.post(self.test_url,
                           data=json_event,
                           headers=self.headers)
        self.assertEqual(rv.status_code, 401)
        self.assertEqual(rv.data, 'Move along, nothing to see here')
        self.assertEqual(rv.mimetype, 'text/plain')

    def test_fail_on_invalid_event_type(self):
        """POST with event not being 'issues' or 'ping' fails."""
        json_event, signature = event_data('new_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'failme',
                             'X-Hub-Signature': signature})
        rv = self.app.post(self.test_url,
                           data=json_event,
                           headers=self.headers)
        self.assertEqual(rv.status_code, 403)
        self.assertEqual(rv.mimetype, 'text/plain')
        self.assertEqual(rv.data, 'This is not the hook we\'re looking for.')

    def test_success_on_ping_event(self):
        """POST with PING events just return a 200 and contains pong."""
        json_event, signature = event_data('new_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'ping',
                             'X-Hub-Signature': signature})
        rv = self.app.post(self.test_url,
                           data=json_event,
                           headers=self.headers)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('pong', rv.data)

    def test_fails_on_unknown_action(self):
        """POST with an unknown action fails."""
        json_event, signature = event_data('new_event_invalid.json')
        self.headers.update({'X-GitHub-Event': 'issues',
                             'X-Hub-Signature': signature})
        rv = self.app.post(self.test_url,
                           data=json_event,
                           headers=self.headers)
        self.assertEqual(rv.status_code, 403)
        self.assertEqual(rv.mimetype, 'text/plain')
        self.assertEqual(
            rv.data, 'We\'ll just circular-file that, but thanks!')

    def test_extract_issue_event_info(self):
        """Extract the right information from an issue event."""
        json_event, signature = event_data('new_issue_event_valid.json')
        payload = json.loads(json_event)
        expected = {'issue_id': 2475,
                    'header': 'Can\'t log in to www.artisanalmustard.com!',
                    'created_at': '2018-07-30T13:22:36Z',
                    'milestone': 'needsdiagnosis',
                    'actor': 'laghee',
                    'action': 'opened',
                    'details': None,
                    'received_at': '2018-07-30T13:23:43Z'}
        actual = helpers.extract_issue_event_info(payload)
        self.assertDictEqual(expected, actual,
                             'Issue event info extracted correctly.')

    def test_add_new_issue(self):
        """Successfully add an issue to the issue table."""
        expected = [2475, 'Can\'t log in to www.artisanalmustard.com!',
                    '2018-07-30T13:22:36Z', 5, True]
        starting_total = Issue.query.count()
        helpers.add_new_event(self.payload)
        new_total = Issue.query.count()
        issue = Issue.query.get(2475)
        actual = [issue.id, issue.header, issue.created_at,
                  issue.milestone_id, issue.is_open]
        self.assertEqual(starting_total+1, new_total,
                         'Exactly one issue added.')
        self.assertListEqual(expected, actual,
                             'New issue data added correctly.')

    def test_add_new_event(self):
        """Successfully add an event to the event table."""
        expected = [2475, 'laghee', 'opened', None, '2018-07-30T13:22:36Z']
        starting_total = Event.query.count()
        helpers.add_new_event(self.payload)
        new_total = Event.query.count()
        event = Event.query.filter_by(issue_id=2475, action='opened')
        actual = [event.issue_id, event.actor, event.action, event.details,
                  event.received_at]
        self.assertEqual(starting_total+1, new_total,
                         'Exactly one issue added.')
        self.assertListEqual(expected, actual,
                             'New issue data added correctly.')

    def test_issue_header_edit(self):
        """Successfully update an issue header in the issue table."""
        pass

    def test_issue_status_change(self):
        """Successfully change an issue's status in the issue table."""
        pass

    def test_issue_milestone_change(self):
        """Successfully change an issue's milestone in the issue table."""
        pass

    def test_issue_label_change(self):
        """Successfully change an issue's label in the issue table."""
        pass

    def test_process_label_event_info(self):
        """Successfully add, edit, and delete labels in the label table."""
        pass

    def test_process_milestone_event_info(self):
        """Successfully change an issue's status in the issue table."""
        pass

    def test_is_github_hook(self):
        """Validation tests for GitHub Webhooks."""
        json_event, signature = event_data('new_event_invalid.json')
        # Lack the X-GitHub-Event
        with self.app as client:
            headers = self.headers.copy()
            headers.update({'X-Hub-Signature': signature})
            client.post(self.test_url,
                        data=json_event,
                        headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-GitHub-Event is missing')
        # Lack the X-Hub-Signature
        with self.app as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues'})
            client.post(self.test_url,
                        data=json_event,
                        headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-Hub-Signature is missing')
        # X-Hub-Signature is wrong
        with self.app as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues',
                            'X-Hub-Signature': 'failme'})
            client.post(self.test_url,
                        data=json_event,
                        headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-Hub-Signature is wrong')
        # Everything is fine
        with self.app as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues',
                            'X-Hub-Signature': signature})
            client.post(self.test_url,
                        data=json_event,
                        headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertTrue(webhook_request,
                            'X-GitHub-Event and X-Hub-Signature are correct')


if __name__ == '__main__':
    unittest.main()
