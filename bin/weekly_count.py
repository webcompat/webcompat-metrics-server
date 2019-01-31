#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Get daily total issues reported on webcompat.
"""

import sys
import datetime
import json
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen


# Config
SEARCH_URL = "https://api.github.com/search/"
QUERY = "issues?q=repo:webcompat/web-bugs+created:{yesterday}"


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
    if json_data["incomplete_results"] is False:
        return json_data["total_count"]
    else:
        return None


def get_yesterday(today_date):
    """Get yesterday's date as a string from today's datetime object in UTC."""
    one_day = datetime.timedelta(days=1)
    return today_date - one_day


def main():
    """Core program."""
    # Extract data from GitHub
    yesterday = get_yesterday(datetime.datetime.now(datetime.timezone.utc))
    # insert yesterday's date into search query in format: 2019-01-30
    query = QUERY.format(yesterday=yesterday.strftime("%Y-%m-%d"))
    url = urljoin(SEARCH_URL, query)
    json_response = get_remote_file(url)
    issue_count = get_issue_count(json_response)
    report_timestamp = yesterday.replace(hour=23, minute=59, second=59)
    # Format the data
    data = "Issues filed yesterday (as of {yesterday}): {issue_count}".format(
        yesterday=report_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        issue_count=issue_count,
    )
    # Log the data on the console
    print(data)


if __name__ == "__main__":
    sys.exit(main())
