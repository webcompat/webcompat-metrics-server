#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Get the total issues reported each day on webcompat.
"""

import sys
import logging
import datetime
import time
import json
import sqlalchemy
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen

from ochazuke import create_app
from ochazuke.models import db
from ochazuke.models import DailyTotal

# Config
SEARCH_URL = "https://api.github.com/search/"
QUERY = "issues?q=repo:webcompat/web-bugs+created:{yesterday}"
LOGGER = logging.getLogger(__name__)


def get_remote_file(url):
    """Request URL."""
    req = Request(url)
    req.add_header("User-agent", "webcompatMonitor")
    req.add_header("Accept", "application/vnd.github.v3+json")
    json_response = urlopen(req, timeout=240)
    return json_response


def get_issue_count(json_response):
    """Get the number of issues (open or closed)."""
    json_data = json.load(json_response)
    if not json_data["incomplete_results"]:
        return json_data["total_count"]
    else:
        return None


def main():
    """Core program to fetch and process data from GitHub."""
    # NOTE: This works as expected if script is scheduled in UTC
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    yesterday = yesterday.isoformat()
    # Insert yesterday's date into search query in format: 2019-01-30
    query = QUERY.format(yesterday=yesterday)
    url = urljoin(SEARCH_URL, query)
    json_response = get_remote_file(url)
    issue_count = get_issue_count(json_response)
    if not issue_count:
        # If results are incomplete, retry after 3 min
        time.sleep(360)
        issue_count = get_issue_count(json_response)
        if not issue_count:
            # On a second failure, log an error
            msg = "Daily count failed for {yesterday}!".format(
                yesterday=yesterday
            )
            LOGGER.warning(msg)
            return
    # Create an app context and store the data in the database
    app = create_app('production')
    with app.app_context():
        total = DailyTotal(day=yesterday, count=issue_count)
        db.session.add(total)
        try:
            db.session.commit()
            msg = "Successfully wrote {day} data in DailyTotal table.".format(
                count=issue_count, day=yesterday)
            LOGGER.info(msg)
        # Catch error and attempt to recover by resetting staged changes.
        except sqlalchemy.exc.SQLAlchemyError as error:
            db.session.rollback()
            msg = ("Yikes! Failed to write data for {day} in "
                   "DailyTotal table: {err}").format(day=yesterday, err=error)
            LOGGER.warning(msg)


if __name__ == "__main__":
    sys.exit(main())
