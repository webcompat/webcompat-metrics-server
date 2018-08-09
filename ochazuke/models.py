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

    def __init__(self, title):
        """Initialize a milestone with its title."""
        self.title = title

    def __repr__(self):
        """Return a milestone as a string of its id followed by its title."""
        return '<Milestone {}: {}>'.format(self.id, self.title)


# Define a table to facilitate the many-to-many link of issues and labels
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

    def __init__(self, name):
        """Initialize a label with its name."""
        self.name = name

    def __repr__(self):
        """Return a label as a string of its table id followed by its name."""
        return '<Label {}: {}>'.format(self.id, self.name)


class Issue(db.Model):
    """Define an issue object and establish table fields/properties.

    An issue has as a unique id number assigned by GitHub.
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

    def __init__(self, id, header, created_at, milestone_id, is_open=True):
        """Initialize an issue with its github number, header (title),
        creation date, milestone id, and status (defaults to open).
        """
        self.id = id
        self.header = header
        self.created_at = created_at
        self.milestone_id = milestone_id
        self.is_open = is_open

    def __repr__(self):
        """Return an issue as a string of its id followed by creation date."""
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
    an update timestamp (when the event occurred) in UTC, recorded by GitHub.
    """
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    issue_id = db.Column(postgresql.INTEGER, db.ForeignKey('issue.id'),
                         nullable=False)
    actor = db.Column(postgresql.TEXT, nullable=False)
    action = db.Column(postgresql.TEXT, nullable=False)
    details = db.Column(postgresql.JSON)
    received_at = db.Column(postgresql.TIMESTAMP(timezone=True),
                            nullable=False)

    def __init__(self, issue_id, actor, action, details, received_at):
        """Initialize an event with an issue number, the actor, the action,
        issue edit or milestone/label details (in json), and when it occurred.
        """
        self.issue_id = issue_id
        self.actor = actor
        self.action = action
        self.details = details
        self.received_at = received_at

    def __repr__(self):
        """Return an event as a string of its table id, the issue it occurred
        on, its action, and when it occurred."""
        return '<Event {} (Issue #{}): {} [{}] >'.format(self.id,
                                                         self.issue_id,
                                                         self.action,
                                                         self.received_at)
