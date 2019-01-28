#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Get count of milestones data.
"""

import datetime
import json
import sys
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen


# Config
URL_REPO = 'https://api.github.com/repos/webcompat/web-bugs/milestones/'
MILESTONES = {
    'non-compat': (1, 'closed'),
    'needstriage': (2, 'open'),
    'needsdiagnosis': (3, 'open'),
    'needscontact': (4, 'open'),
    'contactready': (5, 'open'),
    'sitewait': (6, 'open'),
    'duplicate': (7, 'closed'),
    'invalid': (8, 'closed'),
    'wontfix': (9, 'closed'),
    'worksforme': (10, 'closed'),
    'incomplete': (11, 'closed'),
    'fixed': (12, 'closed'),
    }


def get_remote_file(url):
    """Request URL."""
    req = Request(url)
    req.add_header('User-agent', 'webcompatMonitor')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    json_response = urlopen(req, timeout=240)
    return json_response


def extract_issues_count(json_response, status):
    """Extract the number of open issues."""
    if status == 'open':
        status = 'open_issues'
    else:
        status = 'closed_issues'
    json_data = json.load(json_response)
    return json_data[status]


def newtime(timestamp):
    """convert from local to UTC."""
    local_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    # 2018-02-27T00:00:03Z
    UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()
    new_time = local_time + UTC_OFFSET_TIMEDELTA
    utc_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_time


def main():
    """Core program."""
    # Get the milestone we need from the command line.
    if len(sys.argv) != 2:
        sys.exit('BYE: too many, too few arguments.')
    milestone = sys.argv[1]
    # Check we have the right argument.
    if milestone in MILESTONES:
        # make sure the code is a string.
        urlcode = str(MILESTONES[milestone][0])
        status = MILESTONES[milestone][1]
    else:
        sys.exit('BYE: Not a valid argument.')
    # Extract data from GitHub
    url = urljoin(URL_REPO, urlcode)
    json_response = get_remote_file(url)
    issues_count = extract_issues_count(json_response, status)
    # Compute the date
    now = newtime(datetime.datetime.now().isoformat(timespec='seconds'))
    # Format the data
    data = 'MILESTONE {milestone}: {now} {issues_count}'.format(
        now=now,
        issues_count=issues_count,
        milestone=milestone)
    # code to log the data on the heroku console.
    print(data)


if __name__ == "__main__":
    sys.exit(main())
