#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Some helpers for the tools section."""

import datetime
from urllib.request import Request
from urllib.request import urlopen


def get_remote_data(url):
    """Request URL."""
    req = Request(url)
    req.add_header('User-agent', 'webcompatMonitor')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    json_response = urlopen(req, timeout=240).read()
    return json_response


def newtime(timestamp):
    """convert from local to UTC.

    To be generic whichever server this ends up, we compute the real UTC offset.
    """
    local_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()
    new_time = local_time + UTC_OFFSET_TIMEDELTA
    utc_time = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_time
