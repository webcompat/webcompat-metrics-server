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

import ochazuke
from ochazuke.models import db
# from ochazuke.models import Issue
# from ochazuke.models import Event
from ochazuke.webhooks import helpers


# The key is for testing and computing the signature.
key = ochazuke.app.config['HOOK_SECRET_KEY']


# Some machinery for opening our test files
def event_data(filename):
    """Return a tuple with the content and its signature."""
    current_root = os.path.realpath(os.curdir)
    events_path = 'tests/fixtures/webhooks'
    path = os.path.join(current_root, events_path, filename)
    with open(path, 'r') as f:
        json_event = json.dumps(json.load(f))
    signature = 'sha1={sig}'.format(
        sig=helpers.get_payload_signature(key, json_event.encode('utf-8')))
    return json_event, signature


class TestWebhooks(unittest.TestCase):
    """Tests for our webhooks handler."""

    def setUp(self):
        """Set up tests."""
        self.app = ochazuke.create_app(test_config={})
        # binds app to the current context
        self.app_context = self.app.app_context()
        self.app_context.push()
        # create all the tables for testing
        db.create_all()
        self.client = self.app.test_client()
        self.headers = {'content-type': 'application/json'}
        self.test_url = '/webhooks/ghevents'
        self.payload = {'issue_id': 2475,
                        'header': 'Cannot log in to www.artisanalmustard.com!',
                        'created_at': '2018-07-30T13:22:36Z',
                        'milestone': 'needsdiagnosis',
                        'actor': 'laghee',
                        'action': 'edited',
                        'details': None,
                        'received_at': '2018-08-03T09:17:20Z'}

    def tearDown(self):
        """Tear down tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_forbidden_get(self):
        """GET is forbidden on ghevents webhook."""
        response = self.client.get(self.test_url, headers=self.headers)
        self.assertEqual(response.status_code, 405)

    def test_fail_on_missing_signature(self):
        """POST without signature on ghevents webhook is forbidden."""
        self.headers.update({'X-GitHub-Event': 'ping'})
        response = self.client.post(self.test_url, headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b'Move along, nothing to see here')
        self.assertEqual(response.mimetype, 'text/plain')

    def test_fail_on_bogus_signature(self):
        """POST without bogus signature on ghevents webhook is forbidden."""
        json_event, signature = event_data('new_issue_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'ping',
                             'X-Hub-Signature': 'Boo!'})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, b'Move along, nothing to see here')
        self.assertEqual(response.mimetype, 'text/plain')

    def test_fail_on_invalid_event_type(self):
        """POST with event other than 'issues', 'milestone', 'label', or
        'ping' fails."""
        json_event, signature = event_data('new_issue_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'failme',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(
            response.data, b'This is not the hook we are looking for.')

    def test_success_on_ping_event(self):
        """POST with PING events just return a 200 and contains pong."""
        json_event, signature = event_data('new_issue_event_valid.json')
        self.headers.update({'X-GitHub-Event': 'ping',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pong', response.data)

    def test_ignore_unknown_action(self):
        """POST with an unknown action fails."""
        json_event, signature = event_data('new_issue_event_invalid.json')
        self.headers.update({'X-GitHub-Event': 'issues',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(
            response.data, b'We may just circular-file that, but thanks!')

    def test_ignore_undesirable_issue_action(self):
        """Uninteresting issue actions are accepted but not processed."""
        json_event, signature = event_data('issue_body_edit_meh.json')
        self.headers.update({'X-GitHub-Event': 'issues',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(
            response.data, b'We may just circular-file that, but thanks!')

    def test_ignore_unimportant_milestone_action(self):
        """Uninteresting milestone actions are accepted but not processed."""
        json_event, signature = event_data('milestone_close_meh.json')
        self.headers.update({'X-GitHub-Event': 'milestone',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(
            response.data, b'We may just circular-file that, but thanks!')

    def test_extract_issue_event_info(self):
        """Extract the right information from an issue event."""
        json_event, signature = event_data('new_issue_event_valid.json')
        payload = json.loads(json_event)
        action = payload['action']
        changes = payload['changes']
        expected = {'issue_id': 2475,
                    'header': 'Cannot log in to www.artisanalmustard.com!',
                    'created_at': '2018-07-30T13:22:36Z',
                    'milestone': 'needsdiagnosis',
                    'actor': 'laghee',
                    'action': 'edited',
                    'details': None,
                    'received_at': '2018-08-03T09:17:20Z'}
        actual = helpers.extract_issue_event_info(payload, action, changes)
        self.assertDictEqual(expected, actual,
                             'Issue event info extracted correctly.')

    def test_add_new_issue(self):
        """Successfully add an issue to the issue table."""
        # TODO: Figure out how to mock DB events
        pass
        # expected = [2475, 'Cannot log in to www.artisanalmustard.com!',
        #             '2018-07-30T13:22:36Z', 5, True]
        # starting_total = Issue.query.count()
        # helpers.add_new_event(self.payload)
        # new_total = Issue.query.count()
        # issue = Issue.query.get(2475)
        # actual = [issue.id, issue.header, issue.created_at,
        #           issue.milestone_id, issue.is_open]
        # self.assertEqual(starting_total+1, new_total,
        #                  'Exactly one issue added.')
        # self.assertListEqual(expected, actual,
        #                      'New issue data added correctly.')
        pass

    def test_add_new_event(self):
        """Successfully add an event to the event table."""
        pass
        # expected = [2475, 'laghee', 'opened', None, '2018-07-30T13:22:36Z']
        # starting_total = Event.query.count()
        # helpers.add_new_event(self.payload)
        # new_total = Event.query.count()
        # event = Event.query.filter_by(issue_id=2475, action='opened')
        # actual = [event.issue_id, event.actor, event.action, event.details,
        #           event.received_at]
        # self.assertEqual(starting_total+1, new_total,
        #                  'Exactly one issue added.')
        # self.assertListEqual(expected, actual,
        #                      'New issue data added correctly.')

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
        json_event, signature = event_data('new_issue_event_valid.json')
        # Lack the X-GitHub-Event
        with self.client as client:
            headers = self.headers.copy()
            headers.update({'X-Hub-Signature': signature})
            client.post(self.test_url, data=json_event, headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-GitHub-Event is missing')
        # Lack the X-Hub-Signature
        with self.client as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues'})
            client.post(self.test_url, data=json_event, headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-Hub-Signature is missing')
        # X-Hub-Signature is wrong
        with self.client as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues',
                            'X-Hub-Signature': 'failme'})
            client.post(self.test_url, data=json_event, headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertFalse(webhook_request, 'X-Hub-Signature is wrong')
        # Everything is fine
        with self.client as client:
            headers = self.headers.copy()
            headers.update({'X-GitHub-Event': 'issues',
                            'X-Hub-Signature': signature})
            client.post(self.test_url, data=json_event, headers=headers)
            webhook_request = helpers.is_github_hook(flask.request)
            self.assertTrue(webhook_request,
                            'X-GitHub-Event and X-Hub-Signature are correct')


if __name__ == '__main__':
    unittest.main()
