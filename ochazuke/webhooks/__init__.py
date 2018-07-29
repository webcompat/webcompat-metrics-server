#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Flask Blueprint for our "webhooks" module.webhooks.

See https://developer.github.com/webhooks/ for what is possible.
"""

import json
import logging

from flask import Blueprint
from flask import request

from ochazuke import app

from .helpers import is_github_hook
from .helpers import process_issue_event_info
from .helpers import process_label_event_info
from .helpers import process_milestone_event_info

webhooks = Blueprint('webhooks', __name__, url_prefix='/webhooks')


@webhooks.route('/issues', methods=['POST'])
def issues_hooklistener():
    """Listen for the "issues" webhook event.

    By default, we return a 403 HTTP response.
    """
    if not is_github_hook(request):
        return ('Move along, nothing to see here', 401, {'Content-Type':
                                                         'text/plain'})
    payload = json.loads(request.data)
    event_type = request.headers.get('X-GitHub-Event')

    # Treating issue events
    if event_type == 'issues':
        action = payload.get('action')
        # We don't care about assignment events.
        if action != ('assigned' or 'unassigned'):
                # Extract relevant info to update issue and event tables.
                process_issue_event_info(payload)
                return ('Yay! Data! *munch, munch, munch*', 202,
                        {'Content-Type': 'text/plain'})
        else:
            # We acknowledge receipt even if we don't process all event types.
            return ('We\'ll just circular-file that, but thanks!', 202,
                    {'Content-Type': 'text/plain'})
    elif event_type == 'ping':
        return ('pong', 200, {'Content-Type': 'text/plain'})
    else:
        log = app.logger
        log.setLevel(logging.INFO)
        msg = 'Non-issue-event {event} sent to issue-event endpoint'.format(
            event=event_type)
        log.info(msg)
        # If nothing worked as expected, the default response is 403.
        return ('This is not the hook we\'re looking for...', 403,
                {'Content-Type': 'text/plain'})


@webhooks.route('/label', methods=['POST'])
def label_hooklistener():
    """Listen for the "label" webhook event.

    By default, we return a 403 HTTP response.
    """
    if not is_github_hook(request):
        return ('Nothing to see here.', 401, {'Content-Type': 'text/plain'})
    payload = json.loads(request.data)
    event_type = request.headers.get('X-GitHub-Event')

    # Treating events related to labels
    if event_type == 'label':
        action = payload.get('action')
        # We probably want to keep old labels even if they're deleted on GH.
        if action != 'deleted':
            # Extract relevant info to update label table.
            process_label_event_info(payload)
            return ('Yay! Data! *munch, munch, munch*', 202,
                    {'Content-Type': 'text/plain'})
        else:
            # We don't process deletions, but do acknowledge receipt.
            return ('We\'ll just circular-file that, but thanks!', 202,
                    {'Content-Type': 'text/plain'})
    elif event_type == 'ping':
        return ('pong', 200, {'Content-Type': 'text/plain'})
    else:
        log = app.logger
        log.setLevel(logging.INFO)
        msg = 'Non-label-event {event} sent to label endpoint'.format(
            event=event_type)
        log.info(msg)
        # If nothing worked as expected, the default response is 403.
        return ('This is not the hook we\'re looking for...', 403,
                {'Content-Type': 'text/plain'})


@webhooks.route('/milestone', methods=['POST'])
def milestone_hooklistener():
    """Listen for the "milestone" webhook event.

    By default, we return a 403 HTTP response.
    """
    if not is_github_hook(request):
        return ('Nothing to see here.', 401, {'Content-Type': 'text/plain'})
    payload = json.loads(request.data)
    event_type = request.headers.get('X-GitHub-Event')

    # Treating events related to milestones
    if event_type == 'milestone':
        action = payload.get('action')
        # Other possible actions are opened, closed, and deleted, but we don't
        # use the first two and probably don't want to mirror GH deletions.
        if action == ('created' or 'edited'):
            # We extract relevant info to update the milestone table.
            process_milestone_event_info(payload)
            return ('Yay! Data! *munch, munch, munch*', 202,
                    {'Content-Type': 'text/plain'})
        else:
            # We acknowledge receipt of valid events that we don't process.
            return ('We\'ll just circular-file that, but thanks!', 202,
                    {'Content-Type': 'text/plain'})
    elif event_type == 'ping':
        return ('pong', 200, {'Content-Type': 'text/plain'})
    else:
        log = app.logger
        log.setLevel(logging.INFO)
        msg = 'Non-milestone-event {event} sent to milestone endpoint'.format(
            event=event_type)
        log.info(msg)
        # If nothing worked as expected, the default response is 403.
        return ('This is not the hook we\'re looking for...', 403,
                {'Content-Type': 'text/plain'})
