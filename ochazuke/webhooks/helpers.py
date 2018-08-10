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
from ochazuke.models import db, Milestone, Label, Issue, Event

logger = logging.getLogger(__name__)


def get_payload_signature(key, payload):
    """Compute the payload signature given a key."""
    key = key.encode('utf-8')
    # HMAC requires its key to be encoded bytes
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
    elif (action == 'edited') and changes.get('title'):
        return True
    # We don't know what this is, but we might want to find out
    elif action not in ['assigned', 'unassigned', 'edited']:
        msg = 'Hey, GitHub sent a funky issues-event action: {act}'.format(
            act=action)
        logger.info(msg)
    return False


def extract_issue_event_info(payload, action, changes):
    """Extract information we need when handling webhook for issue events."""
    # Extract the event-specific info and make our own timestamp
    # event_timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    milestone = payload.get('issue')['milestone']
    # If there is no milestone data, let title be None
    if milestone:
        milestone_title = milestone.get('title')
    else:
        milestone_title = None
    # Let details be None for opening/closing, but preserve old title on edits
    if action in ['opened', 'closed', 'reopened', 'edited']:
        details = None
        if changes:
            if changes.get('title'):
                details = {'old title': changes['title']['from']}
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
                        'received_at': payload.get('issue')['updated_at']
                        }
    return issue_event_info


def update_db(info, action):
    """Route extracted data to the appropriate handler for the event type."""
    if action == 'opened':
        add_new_issue(info)
    elif action == 'edited':
        issue_header_edit(info)
    elif action == ('closed' or 'reopened'):
        issue_status_change(info, action)
    elif action == ('milestoned' or 'unmilestoned'):
        issue_milestone_change(info)
    elif action == ('labeled' or 'unlabeled'):
        issue_label_change(info)
    # Store all new desirable valid events
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
    milestone = Milestone.query.filter_by(milestone_title)
    bug = Issue(info.get('issue_id'), info.get('header'),
                info.get('created_at'), milestone_id=milestone.id)
    # Add issue to session staging
    db.session.add(bug)
    try:
        # Perform the actual insertion to the database
        db.session.commit()
        msg = 'New issue ({iss}) successfully added to database.'.format(
            iss=bug)
        logger.info(msg)
        # Catch an error and attempt to recover by backing out of the 'add'.
    except sqlalchemy.exc.SQLAlchemyError as error:
        db.session.rollback()
        msg = 'Yikes! Failed to add issue to database: {err}'.format(
            err=error)
        logger.warning(msg)


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
    # Add event to staging
    db.session.add(event)
    try:
        # Perform the actual insertion to the event table
        db.session.commit()
        msg = 'New event ({evg}) successfully added to database.'.format(
            evt=event)
        logger.info(msg)
        # Catch an error and attempt to recover by backing out of the 'add'.
    except sqlalchemy.exc.SQLAlchemyError as error:
        db.session.rollback()
        msg = 'Yikes! Failed to add event to database: {err}'.format(
            err=error)
        logger.warning(msg)


def issue_header_edit(info):
    """Update issue table with edited header text."""
    # Fetch existing issue from issue table
    bug = Issue.query.get(info.get('issue_id'))
    # Update header and commit changes
    bug.header = info.get('header')
    db.session.commit()


def issue_status_change(info, action):
    """Toggle an issue's 'is_open' status in table between true and false."""
    bug = Issue.query.get(info.get('issue_id'))
    status = {'closed': False, 'reopened': True}
    bug.is_open = status[action]
    db.session.commit()


def issue_milestone_change(info):
    """Add or remove an issue's milestone after an issue milestone event.

    Changing an issue's milestone is handled by GitHub as two discrete events:
    1. Remove the existing milestone
    2. Add a new one
    As a result, an issue can exist (very briefly) in a temporary
    non-milestoned state between the firing of the first event and the second.
    """
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
    if prior_name:
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
    if prior_title:
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
