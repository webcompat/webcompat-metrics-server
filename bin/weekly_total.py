#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Compute and store the total issues reported each week on webcompat.
"""

import sys
import logging
import datetime
import sqlalchemy

from ochazuke import create_app
from ochazuke.models import db
from ochazuke.models import DailyTotal
from ochazuke.models import WeeklyTotal

# Config
LOGGER = logging.getLogger(__name__)


def main():
    """Code to query DB for a week of counts, sum them, and store result."""
    # NOTE: This works as expected if script is scheduled in UTC
    today = datetime.date.today()
    weekday = today.isoweekday()
    if weekday != 1:
        # If not Monday, abandon script and exit
        msg = ("Day of week is {} -- not Monday. "
               "Weekly count script exited.").format(weekday)
        LOGGER.warning(msg)
        return
    monday = today - datetime.timedelta(days=7)
    sunday = today - datetime.timedelta(days=1)
    # Put last Monday and yesterday's dates into format: 2019-01-30
    monday = monday.isoformat()
    sunday = sunday.isoformat()

    # Create an app context and store the data in the database
    app = create_app('production')
    with app.app_context():
        date_range = DailyTotal.day.between(monday, sunday)
        LOGGER.info('MONDAY: {}'.format(monday))
        LOGGER.info('SUNDAY: {}'.format(sunday))
        LOGGER.info('DATE_RANGE {}'.format(date_range))
        week_list = DailyTotal.query.filter(date_range).all()
        LOGGER.info('COUNTS FOR WEEK {}'.format(week_list))
        week_total = 0
        if not week_list:
            # On a query failure, log an error
            msg = "Weekly count query failed for {}!".format(monday)
            LOGGER.warning(msg)
            return
        for day in week_list:
            week_total += day.count
        weekly_count = WeeklyTotal(monday=monday, count=week_total)
        db.session.add(weekly_count)
        try:
            db.session.commit()
            msg = (
                "Successfully wrote count for {} in WeeklyTotal table."
                ).format(monday)
            LOGGER.info(msg)
        # Catch error and attempt to recover by resetting staged changes.
        except sqlalchemy.exc.SQLAlchemyError as error:
            db.session.rollback()
            msg = ("Yikes! Failed to write data for {week} in "
                   "WeeklyTotal table: {err}").format(week=monday, err=error)
            LOGGER.warning(msg)


if __name__ == "__main__":
    sys.exit(main())
