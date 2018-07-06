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
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    title = db.Column(postgresql.TEXT, unique=True, nullable=False)
    issues = db.relationship('Issue', backref='milestone', lazy=True)

    def __repr__(self):
        return '<Milestone {}: {}>'.format(self.id, self.title)


issue_labels = db.Table('issue_labels',
                        db.Column('issue_id',
                                  postgresql.INTEGER,
                                  db.ForeignKey('issue.id'),
                                  primary_key=True),
                        db.Column('label_id', postgresql.INTEGER,
                                  db.ForeignKey('label.id'), primary_key=True)
                        )


class Label(db.Model):
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    name = db.Column(postgresql.TEXT, nullable=False)
    issue_labels = db.relationship('Issue', secondary=issue_labels,
                                   lazy='subquery',
                                   backref=db.backref('labels', lazy=True))

    def __repr__(self):
        return '<Label {}: {}>'.format(self.id, self.name)


class Issue(db.Model):
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    header = db.Column(postgresql.TEXT, nullable=False)
    is_open = db.Column(postgresql.BOOLEAN, nullable=False)
    created_at = db.Column(postgresql.TIMESTAMP(timezone=True), nullable=False)
    milestone_id = db.Column(postgresql.INTEGER, db.ForeignKey(
        'milestone.id'))
    events = db.relationship('Event', backref='issue', lazy=True)

    def __repr__(self):
        return '<Issue {}: Filed {}>'.format(self.id, self.created_at)


class Event(db.Model):
    id = db.Column(postgresql.INTEGER, primary_key=True, unique=True)
    issue_id = db.Column(postgresql.INTEGER, db.ForeignKey('issue.id'),
                         nullable=False)
    actor = db.Column(postgresql.TEXT, nullable=False)
    action = db.Column(postgresql.TEXT, nullable=False)
    details = db.Column(postgresql.JSON)
    received_at = db.Column(postgresql.TIMESTAMP(timezone=True),
                            nullable=False)

    def __repr__(self):
        return '<Event {} (Issue #{}): {} [{}] >'.format(self.id,
                                                         self.issue_id,
                                                         self.action,
                                                         self.received_at)
