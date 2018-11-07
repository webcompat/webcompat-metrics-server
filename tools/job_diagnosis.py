#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Some helpers for the tools section."""

import datetime
import json
import sys
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen

# Config
URL_REPO = 'https://api.github.com/repos/webcompat/web-bugs/'
NEEDSDIAGNOSIS = 'milestones/3'


def get_remote_data(url):
    """Request URL."""
    req = Request(url)
    req.add_header('User-agent', 'webcompatMonitor')
    req.add_header('Accept', 'application/json')
    json_response = urlopen(req, timeout=240).read().decode('utf-8')
    return json_response


def extract_open_issues(json_response):
    """Extract the number of open issues."""
    json_data = json.loads(json_response)
    return json_data["open_issues"]


def newtime(timestamp):
    """Convert from local to UTC."""
    local_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    # 2018-02-27T00:00:03Z
    utc_offset_timedelta = datetime.datetime.utcnow() - datetime.datetime.now()
    new_time = local_time + utc_offset_timedelta
    utc_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_time


def main():
    """Core program."""
    # Extract data from GitHub
    url = urljoin(URL_REPO, NEEDSDIAGNOSIS)
    json_data = get_remote_data(url)
    open_issues = extract_open_issues(json_data)
    now = newtime(datetime.datetime.now().isoformat(timespec='seconds'))
    data = '{now} {open_issues}'.format(now=now, open_issues=open_issues)
    print(data)


if __name__ == "__main__":
    sys.exit(main())
