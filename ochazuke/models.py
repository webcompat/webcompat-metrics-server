#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Models and methods for working with the database."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class DailyTotal(db.Model):
    """Define a DailyTotal for new issues filed.

    An daily total has:

    * a unique table id
    * a day representing the date that corresponds to the total
    * a count of the issues filed on this date
    """

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.DateTime, nullable=False)
    count = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        """Return a representation of a DailyTotal."""
        return "<DailyTotal for {day}: {count}".format(
            day=self.day, count=self.count)
