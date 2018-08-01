#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Models and methods for working with the database."""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql

db = SQLAlchemy()


class Milestone(db.Model):
    """Define a milestone object and establish table fields/properties.

    A milestone has as a unique table id assigned at insertion.
    A milestone also has a title (e.g., 'needsdiagnosis') and zero, one, or
    more issues to which it is assigned (i.e., the milestone table has a
    one-to-many relationship with the issue table).
    """
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    title = db.Column(postgresql.TEXT, unique=True, nullable=False)
    issues = db.relationship('Issue', backref='milestone', lazy=True)

    # make initializing of milestone objects more concise
    def __init__(self, title):
        self.title = title

    # string representation of a milestone is its id followed by title
    def __repr__(self):
        return '<Milestone {}: {}>'.format(self.id, self.title)


# define a table to handle the many-to-many link of issues and labels
issue_labels = db.Table('issue_labels',
                        db.Column('issue_id',
                                  postgresql.INTEGER,
                                  db.ForeignKey('issue.id'),
                                  primary_key=True),
                        db.Column('label_id', postgresql.INTEGER,
                                  db.ForeignKey('label.id'), primary_key=True)
                        )


class Label(db.Model):

    """Define a label object and establish table fields/properties.

    A label has as a unique table id assigned at insertion.
    A label also has a name (e.g., 'browser-firefox') and may have zero, one,
    or more issues to which it is assigned. Likewise, an issue can have more
    than one label (i.e., labels have a many-to-many relationship with issues).
    """
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    name = db.Column(postgresql.TEXT, nullable=False)
    issue_labels = db.relationship('Issue', secondary=issue_labels,
                                   lazy='subquery',
                                   backref=db.backref('labels', lazy=True))

    # make initializing of label objects more concise
    def __init__(self, name):
        self.name = name

    # string representation of a label is its id and name
    def __repr__(self):
        return '<Label {}: {}>'.format(self.id, self.name)


class Issue(db.Model):
    """Define an issue object and establish table fields/properties.

    An issue has as a unique id assigned by GitHub.
    An issue also has a header (e.g., 'google.com - design is broken'),
    a creation date and time (UTC, as recorded by GitHub),
    a milestone (usually),
    zero, one, or more labels,
    and can be set as open or not open.
    An issue can also have zero, one, or more events (i.e., issues have a
    one-to-many relationship with events).
    """
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    header = db.Column(postgresql.TEXT, nullable=False)
    created_at = db.Column(postgresql.TIMESTAMP(timezone=True), nullable=False)
    milestone_id = db.Column(postgresql.INTEGER, db.ForeignKey(
        'milestone.id'))
    is_open = db.Column(postgresql.BOOLEAN, nullable=False)
    events = db.relationship('Event', backref='issue', lazy=True)

    # make initializing of issue objects more concise
    def __init__(self, id, header, created_at, milestone_id, is_open=True):
        self.id = id
        self.header = header
        self.created_at = created_at
        self.milestone_id = milestone_id
        self.is_open = is_open

    # string representation of an issue is its id and creation timestamp
    def __repr__(self):
        return '<Issue {}: Filed {}>'.format(self.id, self.created_at)


class Event(db.Model):
    """Define an event object and establish table fields/properties.

    An event has as a unique id assigned by GitHub (*not sure this is supplied
    in the webhook, so this may end up being auto-generated in our db*).
    An event has a single issue to which it belongs (whose id is stored),
    an actor (i.e., the user who performed the event action),
    an action -- what the event was (e.g., 'demilestoned' or 'closed'),
    details -- json data for any specifics (labeling/milestoning events:
    the name/title of the label/milestone applied or removed, heading edits:
    the old and new heading strings, closed or re-opened: none/null), and
    an update date and time in UTC as recorded by GitHub.
    """
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    issue_id = db.Column(postgresql.INTEGER, db.ForeignKey('issue.id'),
                         nullable=False)
    actor = db.Column(postgresql.TEXT, nullable=False)
    action = db.Column(postgresql.TEXT, nullable=False)
    details = db.Column(postgresql.JSON)
    received_at = db.Column(postgresql.TIMESTAMP(timezone=True),
                            nullable=False)

    # make initializing of event objects more concise
    def __init__(self, issue_id, actor, action, details, received_at):
        self.issue_id = issue_id
        self.actor = actor
        self.action = action
        self.details = details
        self.received_at = received_at

    # string representation of an event is its id, its parent issue's id,
    # the action taken, and timestamp of receipt from GitHub
    def __repr__(self):
        return '<Event {} (Issue #{}): {} [{}] >'.format(self.id,
                                                         self.issue_id,
                                                         self.action,
                                                         self.received_at)
