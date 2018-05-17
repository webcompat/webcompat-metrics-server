#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Tasks to be started by jobs-scheduler."""

import datetime
import json
from urllib.request import urljoin

from tools import DATA_PATH
from tools.helpers import get_remote_data
from tools.helpers import newtime

LAST_PATH = '{path}/{cat_id}/{cat_id}-last.txt'
# TODO: move this to a config file.
CATEGORIES = {'needsdiagnosis': 3}
URL_REPO = 'https://api.github.com/repos/webcompat/web-bugs/'


def update_timeline(cat_id):
    """Tasks to fetch the issues total in a category."""
    if cat_id not in CATEGORIES.keys():
        return False
    last_total = get_last_total(cat_id)
    live_total = get_live_total(cat_id)
    if last_total != live_total:
        # write data into txt_file or json_file
        now = newtime(datetime.datetime.now().isoformat(timespec='seconds'))
        # TODO: commit_last_total(now, live_total, cat_id)
        # TODO: add_live_data(time)
        return True
    return False


def get_last_total(cat_id):
    """Return the last data timestamp for a specific set."""
    with open(LAST_PATH.format(cat_id=cat_id, path=DATA_PATH), 'r') as f:
        txt_line = f.read()
        if txt_line.strip():
            timestamp, total = txt_line.split(' ')
            return int(total)
        else:
            return None
    # if the file doesn't exist
    return None


def get_live_total(cat_id):
    """Return the live total and a timestamp in UTC for a specific set."""
    if cat_id not in CATEGORIES.keys():
        return False
    # Preparing the request
    category = 'milestones/{cat_id}'.format(cat_id=CATEGORIES[cat_id])
    url = urljoin(URL_REPO, category)
    json_response = get_remote_data(url)
    json_data = json.loads(json_response)
    return json_data["open_issues"]


def commit_last_total(now, live_total, cat_id):
    """Write a timestamp in a file"""
    with open(LAST_PATH.format(cat_id=cat_id, path=DATA_PATH), 'r+') as f:
        f.write('{now} {live_total}'.format(now=now, live_total=live_total))
