#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for our webhooks."""

import json
import os
import unittest
from unittest.mock import patch
import flask

import ochazuke
from ochazuke.models import db
from ochazuke.models import Issue
from ochazuke.models import Event
from ochazuke.models import Milestone
from ochazuke.models import Label
from ochazuke.webhook import helpers


# The key is for testing and computing the signature.
key = ochazuke.app.config['HOOK_SECRET_KEY']


# Some machinery for opening our fixture files for posting tests
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


# Quick method for when we don't need the signature bit
def make_payload(filename):
    """Return json-ified payload for testing data extraction."""
    current_root = os.path.realpath(os.curdir)
    events_path = 'tests/fixtures/webhooks'
    path = os.path.join(current_root, events_path, filename)
    with open(path, 'r') as f:
        payload = json.load(f)
    return payload


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
        self.info = {
            'issue_id': 2475,
            'title': 'Cannot log in to www.artisanalmustard.example.com!',
            'created_at': '2018-07-30T13:22:36Z',
            'milestone': 'needsdiagnosis',
            'actor': 'laghee',
            'action': 'edited',
            'details': None,
            'received_at': '2018-08-03T09:17:20Z'
        }

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
        """POST with bogus signature on ghevents webhook is forbidden."""
        json_event, signature = event_data('issue_body_edited.json')
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
        json_event, signature = event_data('issue_body_edited.json')
        self.headers.update({'X-GitHub-Event': 'failme',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(
            response.data, b'This is not the hook we seek.')

    def test_success_on_ping_event(self):
        """POST with PING events just return a 200 and contains pong."""
        json_event, signature = event_data('issue_body_edited.json')
        self.headers.update({'X-GitHub-Event': 'ping',
                             'X-Hub-Signature': signature})
        response = self.client.post(self.test_url,
                                    data=json_event,
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pong', response.data)

    def test_ignore_unknown_action(self):
        """POST with an unknown action fails."""
        json_event, signature = event_data('issue_event_invalid_action.json')
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
        json_event, signature = event_data('issue_body_edited.json')
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
        json_event, signature = event_data('milestone_closed.json')
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
        json_event, signature = event_data('issue_body_edited.json')
        payload = json.loads(json_event)
        action = payload['action']
        changes = payload['changes']
        expected = {
            'issue_id': 2475,
            'title': 'Cannot log in to www.artisanalmustard.example.com!',
            'created_at': '2018-07-30T13:22:36Z',
            'milestone': 'needsdiagnosis',
            'actor': 'laghee',
            'action': 'edited',
            'details': None,
            'received_at': '2018-08-03T09:17:20Z'
        }
        actual = helpers.extract_issue_event_info(payload, action, changes)
        self.assertDictEqual(expected, actual,
                             'Issue event info extracted correctly.')

    @patch('ochazuke.webhook.helpers.get_milestone_by_title')
    @patch('ochazuke.webhook.helpers.make_change_to_database')
    def test_add_new_issue(self, mock_change, mock_get):
        """A database issue object is created correctly and inserted."""
        test_milestone = Milestone('needsdiagnosis')
        test_milestone.id = 42
        mock_get.return_value = test_milestone
        helpers.add_new_issue(self.info)
        db_calls = mock_change.call_count
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(db_calls, 1)
        self.assertEqual(operation, 'Add')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertEqual(
            issue_object.title,
            'Cannot log in to www.artisanalmustard.example.com!')
        self.assertEqual(issue_object.created_at, '2018-07-30T13:22:36Z')
        self.assertEqual(issue_object.milestone_id, 42)

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    def test_add_new_event(self, mock_change):
        """A database event object is created correctly and inserted."""
        helpers.add_new_event(self.info)
        db_calls = mock_change.call_count
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        event_object = args[1]
        self.assertEqual(db_calls, 1)
        self.assertEqual(operation, 'Add')
        self.assertIsInstance(event_object, Event)
        self.assertEqual(event_object.issue_id, 2475)
        self.assertEqual(event_object.actor, 'laghee')
        self.assertEqual(event_object.action, 'edited')
        self.assertEqual(event_object.details, None)
        self.assertEqual(event_object.received_at, '2018-08-03T09:17:20Z')

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    @patch('ochazuke.webhook.helpers.get_issue_by_id')
    def test_issue_title_edit(self, mock_get, mock_change):
        """Successfully update an issue title in the issue table."""
        issue = Issue(2475, 'Snappy title with egregious spelling error',
                      '2018-07-30T13:22:36Z', 17)
        mock_get.return_value = issue
        helpers.issue_title_edit(self.info)
        db_calls = mock_change.call_count
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(db_calls, 1)
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertEqual(issue_object.title,
                         'Cannot log in to www.artisanalmustard.example.com!')

    @patch('ochazuke.webhook.helpers.get_issue_by_id')
    @patch('ochazuke.webhook.helpers.make_change_to_database')
    def test_issue_status_change(self, mock_change, mock_get):
        """Successfully change an issue's status in the issue table."""
        # Status change to 'closed'
        issue = Issue(2475,
                      'Cannot log in to www.artisanalmustard.example.com!',
                      '2018-07-30T13:22:36Z', 17)
        mock_get.return_value = issue
        self.info.update({'action': 'opened'})
        helpers.issue_status_change(self.info, 'closed')
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertFalse(issue_object.is_open)
        # Status change to open ('reopened')
        self.info.update({'is_open': False})
        helpers.issue_status_change(self.info, 'reopened')
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertTrue(issue_object.is_open)

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    @patch('ochazuke.webhook.helpers.get_issue_by_id')
    def test_issue_milestone_change(self, mock_get_issue, mock_change):
        """Successfully change an issue's milestone in the issue table."""
        # Change on 'demilestoned' action
        issue = Issue(2475,
                      'Cannot log in to www.artisanalmustard.example.com!',
                      '2018-07-30T13:22:36Z', 42)
        mock_get_issue.return_value = issue
        self.info.update({'action': 'demilestoned'})
        helpers.issue_milestone_change(self.info)
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertIsNone(issue_object.milestone_id)
        # Change on 'milestoned' action
        with patch('ochazuke.webhook.helpers.get_milestone_by_title') \
                as mock_get_milestone:
            self.info.update({'action': 'milestoned',
                              'milestone_id': None})
            milestone = Milestone('needsdiagnosis')
            milestone.id = 42
            mock_get_milestone.return_value = milestone
            helpers.issue_milestone_change(self.info)
            db_args = mock_change.call_args
            args, kwargs = db_args
            operation = args[0]
            issue_object = args[1]
            self.assertEqual(operation, 'Update')
            self.assertIsInstance(issue_object, Issue)
            self.assertEqual(issue_object.id, 2475)
            self.assertEqual(issue_object.milestone_id, 42)

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    @patch('ochazuke.webhook.helpers.get_label_by_name')
    @patch('ochazuke.webhook.helpers.get_issue_by_id')
    def test_issue_label_change(self, mock_get_issue, mock_get_label,
                                mock_change):
        """Successfully change an issue's label in the issue table."""
        # Labeled event
        issue = Issue(2475,
                      'Cannot log in to www.artisanalmustard.example.com!',
                      '2018-07-30T13:22:36Z', 42)
        old_label = Label('wut-idk')
        old_label.id = 8
        issue.labels.append(old_label)
        mock_get_issue.return_value = issue
        label = Label('rotfl')
        label.id = 16
        mock_get_label.return_value = label
        self.info.update({'action': 'labeled',
                          'details': {'label name': 'rotfl'}
                          })
        helpers.issue_label_change(self.info)
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertIn(label, issue_object.labels)
        # Unlabeled event
        self.info.update({'action': 'unlabeled'})
        helpers.issue_label_change(self.info)
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        issue_object = args[1]
        self.assertEqual(operation, 'Update')
        self.assertIsInstance(issue_object, Issue)
        self.assertEqual(issue_object.id, 2475)
        self.assertNotIn(label, issue_object.labels)

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    def test_process_label_event_info(self, mock_change):
        """Successfully add, edit, and delete labels in the label table."""
        # Label is created
        payload = make_payload('label_created.json')
        helpers.process_label_event_info(payload)
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        label_object = args[1]
        self.assertEqual(operation, 'Add')
        self.assertIsInstance(label_object, Label)
        self.assertEqual(label_object.name, 'omgwtf')
        # Label name is edited
        with patch('ochazuke.webhook.helpers.get_label_by_name') as mock_get:
            label = Label('omgwtf')
            mock_get.return_value = label
            payload = make_payload('label_name_edited.json')
            helpers.process_label_event_info(payload)
            db_args = mock_change.call_args
            args, kwargs = db_args
            operation = args[0]
            label_object = args[1]
            self.assertEqual(operation, 'Update')
            self.assertIsInstance(label_object, Label)
            self.assertEqual(label_object.name, 'wut-lol')
        # Label color is edited, so we ignore this
        mock_change.reset_mock()
        payload = make_payload('label_color_edited.json')
        helpers.process_label_event_info(payload)
        mock_change.assert_not_called()
        # Label is deleted
        with patch('ochazuke.webhook.helpers.get_label_by_name') as mock_get:
            label = Label('wut-lol')
            mock_get.return_value = label
            payload = make_payload('label_deleted.json')
            helpers.process_label_event_info(payload)
            db_args = mock_change.call_args
            args, kwargs = db_args
            operation = args[0]
            label_object = args[1]
            self.assertEqual(operation, 'Remove')
            self.assertIsInstance(label_object, Label)
            self.assertEqual(label_object.name, 'wut-lol')

    @patch('ochazuke.webhook.helpers.make_change_to_database')
    def test_process_milestone_event_info(self, mock_change):
        """Successfully add, edit, and delete milestones in the table."""
        # Milestone is created
        payload = make_payload('milestone_created.json')
        helpers.process_milestone_event_info(payload)
        db_args = mock_change.call_args
        args, kwargs = db_args
        operation = args[0]
        milestone_object = args[1]
        self.assertEqual(operation, 'Add')
        self.assertIsInstance(milestone_object, Milestone)
        self.assertEqual(milestone_object.title, 'needsguac')
        # Milestone title is edited
        with patch(
                'ochazuke.webhook.helpers.get_milestone_by_title') as mock_get:
            milestone = Milestone('needstaco')
            mock_get.return_value = milestone
            payload = make_payload('milestone_title_edited.json')
            helpers.process_milestone_event_info(payload)
            db_args = mock_change.call_args
            args, kwargs = db_args
            operation = args[0]
            milestone_object = args[1]
            self.assertEqual(operation, 'Update')
            self.assertIsInstance(milestone_object, Milestone)
            self.assertEqual(milestone_object.title, 'needsdietcoke')
        # Milestone due date is edited, but we could not care less
        mock_change.reset_mock()
        payload = make_payload('milestone_due_date_edited.json')
        helpers.process_milestone_event_info(payload)
        mock_change.assert_not_called()
        # Milestone is deleted
        with patch(
                'ochazuke.webhook.helpers.get_milestone_by_title') as mock_get:
            milestone = Milestone('needszinfandel')
            mock_get.return_value = milestone
            payload = make_payload('milestone_deleted.json')
            helpers.process_milestone_event_info(payload)
            db_args = mock_change.call_args
            args, kwargs = db_args
            operation = args[0]
            milestone_object = args[1]
            self.assertEqual(operation, 'Remove')
            self.assertIsInstance(milestone_object, Milestone)
            self.assertEqual(milestone_object.title, 'needszinfandel')

    def test_is_github_hook(self):
        """Validation tests for GitHub Webhooks."""
        json_event, signature = event_data('issue_body_edited.json')
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
