#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Flask Blueprint for our GitHub webhooks.

See https://developer.github.com/webhooks/ for what is possible.
"""

import json
import logging

from flask import Blueprint
from flask import request

from ochazuke.webhooks.helpers import is_github_hook
from ochazuke.webhooks.helpers import is_desirable_issue_event
from ochazuke.webhooks.helpers import extract_issue_event_info
from ochazuke.webhooks.helpers import update_db
from ochazuke.webhooks.helpers import process_label_event_info
from ochazuke.webhooks.helpers import process_milestone_event_info

logger = logging.getLogger(__name__)
webhooks = Blueprint('webhooks', __name__, url_prefix='/webhooks')
TEXT_PLAIN = {'Content-Type': 'text/plain'}
MEH_RESPONSE = ('We may just circular-file that, but thanks!', 202,
                TEXT_PLAIN)
NO_AUTH = ('This is not the hook we seek.', 403, TEXT_PLAIN)


@webhooks.route('/ghevents', methods=['POST'])
def issues_hooklistener():
    """Listen for `issues`, `label`, and `milestone` events from GitHub.

    By default, we return a 403 HTTP response.
    """
    if not is_github_hook(request):
        return ('Move along, nothing to see here', 401, TEXT_PLAIN)
    event_type = request.headers.get('X-GitHub-Event')
    try:
        payload = json.loads(request.data)
        action = payload.get('action')
        changes = payload.get('changes')
    except Exception as error:
        msg = 'Huh? GitHub sent us some wonky garbage, folks: {err}'.format(
            err=error)
        logger.info(msg)
    # Treating issue events
    if event_type == 'issues':
        if is_desirable_issue_event(action, changes):
            # Extract relevant info to update issue and event tables.
            issue_event_info = extract_issue_event_info(payload, action,
                                                        changes)
            update_db(issue_event_info, action)
            return ('Yay! Data! *munch, munch, munch*', 200, TEXT_PLAIN)
        else:
            # We acknowledge receipt for events that we don't process.
            return MEH_RESPONSE
    # Treating label events
    elif event_type == 'label':
        # Extract relevant info to update label table.
        process_label_event_info(payload)
    elif event_type == 'milestone':
        # Other possible actions are opened and closed, but we don't use them.
        if action in ['created', 'edited', 'deleted']:
            # We extract relevant info to update the milestone table.
            process_milestone_event_info(payload)
        else:
            return MEH_RESPONSE
    elif event_type == 'ping':
        return ('pong', 200, TEXT_PLAIN)
    else:
        # Log unexpected events.
        msg = 'Hey! GitHub sent us a funky (or new) event: {event}'.format(
            event=event_type)
        logger.info(msg)
        # If nothing worked as expected, the default response is 403.
        return NO_AUTH
