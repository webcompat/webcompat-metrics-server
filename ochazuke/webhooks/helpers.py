#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Helpers methods for webhooks."""

import hashlib
import hmac
import logging

from datetime import datetime

from ochazuke import app
from ochazuke.models import db, Milestone, Label, Issue, Event


def get_payload_signature(key, payload):
    """Compute the payload signature given a key."""
    mac = hmac.new(key, msg=payload, digestmod=hashlib.sha1)
    return mac.hexdigest()


def signature_check(key, post_signature, payload):
    """Check the HTTP POST legitimacy."""
    if post_signature.startswith('sha1='):
        sha_name, signature = post_signature.split('=')
    else:
        return False
    if not signature:
        return False
    # HMAC requires its key to be bytes, but data is strings.
    hexmac = get_payload_signature(key, payload)
    return compare_digest(hexmac, signature.encode('utf-8'))


def compare_digest(x, y):
    """Create a hmac comparison.

    Approximates hmac.compare_digest (Py 2.7.7+) until we upgrade.
    TODO: SEE IF THIS NEEDS TO BE ADAPTED FOR PY3.6
    """
    if not (isinstance(x, bytes) and isinstance(y, bytes)):
        raise TypeError("both inputs should be instances of bytes")
    if len(x) != len(y):
        return False
    result = 0
    for a, b in zip(bytearray(x), bytearray(y)):
        result |= a ^ b
    return result == 0


def is_github_hook(request):
    """Validate the github webhook HTTP POST request."""
    if request.headers.get('X-GitHub-Event') is None:
        return False
    post_signature = request.headers.get('X-Hub-Signature')
    if post_signature:
        key = app.config['HOOK_SECRET_KEY']
        return signature_check(key, post_signature, request.data)
    return False


def extract_issue_event_info(payload):
    """Extract information we need when handling webhook for issue events."""
    # Extract the event-specific info and make our own timestamp
    event_timestmp = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    action = payload.get('action')
    milestone = payload.get('issue')['milestone']
    # If there is no milestone data, let title be None
    if milestone is not None:
        milestone_title = milestone.get('title')
    else:
        milestone_title = None
    # Let details be None for opening/closing, but preserve old title on edits
    if action in ['opened', 'closed', 'reopened', 'edited']:
        changes = payload.get('changes')
        if changes is not None:
            details = {'old title': changes['title']['from']}
        else:
            details = None
    elif action == ('milestoned' or 'demilestoned'):
        details = {'milestone title': payload.get(
            'issue')['milestone']['title']}
    else:
        details = {'label name': payload.get('label')['name']}
    # Create a concise issue event dictionary
    issue_event_info = {'issue_id': payload.get('issue')['number'],
                        'header': payload.get('issue')['title'],
                        'created_at': payload.get('issue')['created_at'],
                        'milestone': milestone_title,
                        'actor': payload.get('sender')['login'],
                        'action': action,
                        'details': details,
                        'received_at': event_timestmp}
    return issue_event_info


def update_db(info, action):
    """Route extracted data to the appropriate handler for the event type."""
    if action == 'opened':
        add_new_issue(info)
    elif action == 'edited':
        issue_header_edit(info)
    elif action == ('closed' or 'reopened'):
        issue_status_change(info)
    elif action == ('milestoned' or 'unmilestoned'):
        issue_milestone_change(info)
    elif action == ('labeled' or 'unlabeled'):
        issue_label_change(info)
    # Store all new events except assigned/unassigned (filtered out in route)
    add_new_event(info)


def add_new_issue(info):
    """Create an issue object to insert into db from an 'opened' issue event.

    When a new issue is opened, we insert it into our issue table, including:
    - github number (int, 'id')
    - title (text, 'header')
    - status (boolean, 'is_open')
    - creation timestamp ('created_at')
    - milestone id number (int, 'milestone_id')
    """
    milestone_title = info.get('milestone')
    milestone = Milestone.query.filter_by(milestone_title).one()
    bug = Issue(info.get('issue_id'), info.get('header'),
                info.get('created_at'), milestone_id=milestone.id)
    # TODO: log failures/errors as well?
    # Add issue to staging
    db.session.add(bug)
    # Perform the actual insertion to the database
    db.session.commit()
    log = app.logger
    log.setLevel(logging.INFO)
    msg = 'New issue ({iss}) successfully added to database.'.format(iss=bug)
    log.info(msg)


def add_new_event(info):
    """Create an event object to insert into db from a new issue event.

    When a new event is signaled, we insert it into the event table, including:
    - github issue number (int, 'issue_id')
    - username of user who triggered the event (text, 'actor')
    - what the event was (text, 'action')
    - any relevant details (json, 'details') -- see models.Event
    - when we received the event (timestamp, 'received_at')
    We assign each event a unique id automatically upon insertion to the db.
    """
    event = Event(info.get('issue_id'), info.get('actor'), info.get('action'),
                  info.get('details'), info.get('received_at'))
    # TODO: log failures/errors as well?
    # Add event to staging
    db.session.add(event)
    # Insert event into event table
    db.session.commit()
    log = app.logger
    log.setLevel(logging.INFO)
    msg = 'New event ({evt}) successfully added to database.'.format(evt=event)
    log.info(msg)


def issue_header_edit(info):
    """Update issue table with edited header text."""
    # Fetch existing issue from issue table
    bug = Issue.query.get(info.get('issue_id'))
    # Update header and commit changes
    bug.header = info.get('header')
    db.session.commit()


def issue_status_change(info):
    """Toggle an issue's 'is_open' status in table between true and false."""
    bug = Issue.query.get(info.get('issue_id'))
    bug.is_open = (False if bug.is_open else True)
    db.session.commit()


def issue_milestone_change(info):
    """Add or remove an issue's milestone after an issue milestone event."""
    issue = Issue.query.get(info.get('issue_id'))
    if info.get('action') == 'milestoned':
        issue.milestone = info.get('milestone_id')
    else:
        issue.milestone = None
    db.session.commit()


def issue_label_change(info):
    """Add or remove an issue label after an issue label event."""
    label_name = info.get('details')['label name']
    label_id = Label.query.filter_by(name=label_name).one().id
    issue = Issue.query.get(info.get('issue_id'))
    if info.get('action') == 'labeled':
        issue.labels.append(label_id)
    else:
        issue.labels.remove(label_id)
    db.session.commit()


def process_label_event_info(payload):
    """Extract necessary information from webhook for label events."""
    action = payload.get('action')
    label_name = payload.get('label')['name']
    prior_name = payload.get('changes').get('name', None)
    if prior_name is not None:
        prior_name = payload.get('changes')['name']['from']
        name_edited = True
    if action == 'created':
        label = Label(label_name)
        db.session.add(label)
    elif (action == 'edited') and name_edited:
        label = Label.query.filter_by(name=prior_name)
        label.name = label_name
    else:
        label = Label.query.filter_by(name=label_name)
        db.session.remove(label)
    db.session.commit()


def process_milestone_event_info(payload):
    """Extract necessary information from webhook for milestone events."""
    action = payload.get('action')
    milestone_title = payload.get('milestone')['title']
    prior_title = payload.get('changes').get('title', None)
    if prior_title is not None:
        title_edited = True
    if action == 'created':
        milestone = Milestone(milestone_title)
        db.session.add(milestone)
    elif (action == 'edited') and title_edited:
        milestone = Milestone.query.filter_by(title=prior_title)
        milestone.title = milestone_title
    else:
        milestone = Milestone.query.filter_by(title=milestone_title)
        db.session.remove(milestone)
    db.session.commit()
