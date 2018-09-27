#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Some helpers for the tools section."""

from urllib.request import Request
from urllib.request import urlopen


def get_remote_data(url):
    """Request URL."""
    req = Request(url)
    req.add_header('User-agent', 'webcompatMonitor')
    req.add_header('Accept', 'application/json')
    json_response = urlopen(req, timeout=240).read()
    return json_response
