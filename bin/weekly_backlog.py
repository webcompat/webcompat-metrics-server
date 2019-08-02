#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Import historical weekly reports data.
"""

import json
import sys
import sqlalchemy
import logging
from urllib.request import Request
from urllib.request import urlopen

from ochazuke import create_app
from ochazuke.models import db
from ochazuke.models import WeeklyTotal

# Config
URL_DATA = 'http://laghee.pythonanywhere.com/tmp/weekly_issues'
TIMELINE = 'timeline'
LOGGER = logging.getLogger(__name__)


def get_remote_file(url):
    """Request URL."""
    req = Request(url)
    json_response = urlopen(req, timeout=240)
    return json_response


def extract_timeline(json_response):
    """Extract the timeline list."""
    json_data = json.load(json_response)
    return json_data[TIMELINE]


def main():
    """Core program."""
    json_response = get_remote_file(URL_DATA)
    weeklytotal_timeline = extract_timeline(json_response)
    # Create an app context and store the data in the database
    app = create_app('development')
    with app.app_context():
        for item in weeklytotal_timeline:
            wk_total = WeeklyTotal(
                monday=item['timestamp'],
                count=item['count'])
            db.session.add(wk_total)
            try:
                db.session.commit()
                msg = ("Successfully wrote imported WEEKLY_TOTAL count for "
                       "{} to WeeklyTotal table.").format(
                    wk_total.monday)
                LOGGER.info(msg)
        # Catch error and attempt to recover by resetting staged changes
            except sqlalchemy.exc.SQLAlchemyError as error:
                db.session.rollback()
                msg = ("Yikes! Failed to write imported WEEKLY_TOTAL count "
                       "for {} in WeeklyTotal table. {error}").format(
                    wk_total.monday,
                    error=error)
                LOGGER.warning(msg)


if __name__ == "__main__":
    sys.exit(main())
