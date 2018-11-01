#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Helper methods for webhooks."""

import hashlib
import hmac
import logging
import sqlalchemy

import ochazuke
from ochazuke.models import db
from ochazuke.models import Milestone
from ochazuke.models import Label
from ochazuke.models import Issue
from ochazuke.models import Event

logger = logging.getLogger(__name__)
ADD = 'Add'
REMOVE = 'Remove'
UPDATE = 'Update'


def get_payload_signature(key, payload):
    """Compute the payload signature given a key."""
    # HMAC requires its key to be encoded bytes
    mac = hmac.new(b'key', msg=payload, digestmod=hashlib.sha1)
    return mac.hexdigest()


def signature_check(key, post_signature, payload):
    """Check the HTTP POST legitimacy."""
    if post_signature.startswith('sha1='):
        sha_name, signature = post_signature.split('=')
    else:
        return False
    if not signature:
        return False
    hexmac = get_payload_signature(key, payload)
    return hmac.compare_digest(hexmac, signature)


def is_github_hook(request):
    """Validate the github webhook HTTP POST request."""
    if request.headers.get('X-GitHub-Event') is None:
        return False
    post_signature = request.headers.get('X-Hub-Signature')
    if post_signature:
        key = ochazuke.app.config['HOOK_SECRET_KEY']
        return signature_check(key, post_signature, request.data)
    return False


def is_desirable_issue_event(action, changes):
    """Determine whether issue event is worth processing."""
    if action in ['opened', 'closed', 'reopened', 'labeled', 'unlabeled',
                  'milestoned', 'unmilestoned']:
        return True
    # We don't care about issue body edits since we only store titles
    elif (action == 'edited') and changes:
        if changes.get('title'):
            return True
    # We don't know what this is, but we might want to find out
    elif action not in ['assigned', 'unassigned', 'edited']:
        msg = 'Hey, GitHub sent a funky issues-event action: {act}'.format(
            act=action)
        logger.info(msg)
    return False


def extract_issue_event_info(payload, action, changes):
    """Extract information we need when handling webhook for issue events."""
    milestone = payload['issue']['milestone']
    # If there is no milestone data, let title be None
    if milestone:
        milestone_title = milestone.get('title')
    else:
        milestone_title = None
    if action in ['opened', 'closed', 'reopened', 'edited']:
        # Details attribute is stored in events table for extra event context
        details = None
        if changes:
            # Details are None for opening/closing, store old title on edits
            if changes.get('title'):
                details = {'old title': changes['title']['from']}
    elif action == ('milestoned' or 'demilestoned'):
        details = {'milestone title': payload['issue']['milestone']['title']}
    else:
        details = {'label name': payload['label']['name']}
    # Create a concise issue event dictionary
    issue_event_info = {'issue_id': payload['issue']['number'],
                        'title': payload['issue']['title'],
                        'created_at': payload['issue']['created_at'],
                        'milestone': milestone_title,
                        'actor': payload['sender']['login'],
                        'action': action,
                        'details': details,
                        'received_at': payload['issue']['updated_at']
                        }
    return issue_event_info


def add_new_issue(info):
    """Create an issue object to insert into db from an 'opened' issue event.

    When a new issue is opened, we insert it into our issue table, including:
    - github number (int, 'id')
    - title (text, 'title')
    - creation timestamp ('created_at')
    - milestone id number (int, 'milestone_id')
    - status (boolean, 'is_open', defaults to True)
    """
    milestone_title = info['milestone']
    if milestone_title:
        milestone_id = get_milestone_by_title(milestone_title).id
    else:
        milestone_id = None
    bug = Issue(info['issue_id'], info['title'], info['created_at'],
                milestone_id)
    make_change_to_database(ADD, bug)


def add_new_event(info):
    """Create an event object to insert into db from a new issue event.

    When a new event is signaled, we insert it into the event table, including:
    - github issue number (int, 'issue_id')
    - username of user who triggered the event (text, 'actor')
    - what the event was (text, 'action')
    - any relevant details (json, 'details') -- see models.Event
    - when the event occurred (timestamp, 'received_at')
    We assign each event a unique id automatically upon insertion to the db.
    """
    event = Event(info['issue_id'], info['actor'], info['action'],
                  info['details'], info['received_at'])
    make_change_to_database(ADD, event)


def issue_title_edit(info):
    """Update issue table with edited title text."""
    bug = get_issue_by_id(info['issue_id'])
    bug.title = info['title']
    make_change_to_database(UPDATE, bug)


def issue_status_change(info, action):
    """Toggle an issue's 'is_open' status in table between true and false."""
    bug = get_issue_by_id(info['issue_id'])
    status = {'closed': False, 'reopened': True}
    bug.is_open = status[action]
    make_change_to_database(UPDATE, bug)


def issue_milestone_change(info):
    """Add or remove an issue's milestone after an issue milestone event.

    Changing an issue's milestone is handled by GitHub as two discrete events:
    1. Remove the existing milestone
    2. Add a new one
    As a result, an issue can exist (very briefly) in a temporary
    non-milestoned state between the firing of the first event and the second.
    """
    issue = get_issue_by_id(info['issue_id'])
    if info['action'] == 'milestoned':
        milestone = get_milestone_by_title(info['milestone'])
        issue.milestone_id = milestone.id
    else:
        issue.milestone_id = None
    make_change_to_database(UPDATE, issue)


def issue_label_change(info):
    """Add or remove an issue label after an issue label event."""
    label_name = info['details']['label name']
    label = get_label_by_name(label_name)
    issue = get_issue_by_id(info['issue_id'])
    if info['action'] == 'labeled':
        issue.labels.append(label)
    else:
        issue.labels.remove(label)
    make_change_to_database(UPDATE, issue)


def process_label_event_info(payload):
    """Extract necessary information from webhook for label events."""
    action = payload['action']
    label_name = payload['label']['name']
    changes = payload.get('changes')
    prior_name = None
    if changes:
        # Changes to label color also sent - as ['changes']['color']['from']
        if changes.get('name'):
            prior_name = payload['changes']['name']['from']
    if action == 'created':
        label = Label(label_name)
        make_change_to_database(ADD, label)
    elif prior_name:
        label = get_label_by_name(prior_name)
        label.name = label_name
        make_change_to_database(UPDATE, label)
    elif action == 'deleted':
        label = get_label_by_name(label_name)
        make_change_to_database(REMOVE, label)


def process_milestone_event_info(payload):
    """Extract necessary information from webhook for milestone events."""
    action = payload['action']
    milestone_title = payload['milestone']['title']
    changes = payload.get('changes')
    prior_title = None
    if changes:
        # Two other possible changes keys - ['description'] and ['due_on']
        if changes.get('title'):
            prior_title = payload['changes']['title']
    if action == 'created':
        milestone = Milestone(milestone_title)
        make_change_to_database(ADD, milestone)
    elif prior_title:
        milestone = get_milestone_by_title(prior_title)
        milestone.title = milestone_title
        make_change_to_database(UPDATE, milestone)
    elif action == 'deleted':
        milestone = get_milestone_by_title(milestone_title)
        make_change_to_database(REMOVE, milestone)


def get_issue_by_id(id):
    """Return an issue object from its id and handle any errors."""
    issue = None
    try:
        issue = Issue.query.filter_by(id=id).one()
    except sqlalchemy.orm.exc.NoResultsFound as error:
        msg = 'Yikes! No issue found for id #{id_num}! ({err})'.format(
            id_num=id, err=error)
        logger.warning(msg)
    except sqlalchemy.orm.exc.MultipleResultsFound as error:
        msg = 'Yikes! Multiple issues found for id #{id_num}! ({err})'.format(
            id_num=id, err=error)
        logger.warning(msg)
    return issue


def get_label_by_name(name):
    """Return a label object from its name and handle any errors."""
    label = None
    try:
        label = Label.query.filter_by(name=name).one()
    except sqlalchemy.orm.exc.NoResultFound as error:
        msg = 'Yikes! No label found for: {name}! ({err})'.format(
            name=name, err=error)
        logger.warning(msg)
    except sqlalchemy.orm.exc.MultipleResultsFound as error:
        msg = 'Yikes! Multiple labels found for: {name}! ({err})'.format(
            name=name, err=error)
        logger.warning(msg)
    return label


def get_milestone_by_title(title):
    """Return a milestone object from its title and handle any errors."""
    milestone = None
    try:
        milestone = Milestone.query.filter_by(title=title).one()
    except sqlalchemy.orm.exc.NoResultFound as error:
        msg = 'Yikes! No milestone found for: {title}! ({err})'.format(
            title=title, err=error)
        logger.warning(msg)
    except sqlalchemy.orm.exc.MultipleResultsFound as error:
        msg = 'Yikes! Multiple milestones found for: {title}! ({err})'.format(
            title=title, err=error)
        logger.warning(msg)
    return milestone


def make_change_to_database(operation, item):
    """Attempt to write change to database and handle any resulting errors."""
    if operation == ADD:
        db.session.add(item)
    elif operation == REMOVE:
        db.session.remove(item)
    try:
        db.session.commit()
        msg = 'Successfully wrote {op}: {itm} to database.'.format(
            op=operation, itm=item)
        logger.info(msg)
        # Catch error and attempt to recover by reseting staged changes.
    except sqlalchemy.exc.SQLAlchemyError as error:
        db.session.rollback()
        msg = 'Yikes! Failed to write {op}: {itm} to database: {err}'.format(
            op=operation, itm=item, err=error)
        logger.warning(msg)
