#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Some helpers for the data processing section."""

import datetime
import json


def get_days(from_date, to_date):
    """Create the list of dates spanning two dates.

    A date is a string 'YYYY-MM-DD'
    A date is considered to be starting at 00:00:00.
    An invalid date format should be ignored and return None.
    The same from_date and to_date should return from_date.
    """
    date_format = '%Y-%m-%d'
    try:
        start = datetime.datetime.strptime(from_date, date_format)
        end = datetime.datetime.strptime(to_date, date_format)
        # we assume that the person is requesting one day
        if start == end:
            return [from_date]
    except Exception:
        return None
    else:
        dates = []
        delta = end - start
        days = delta.days
        if days < 0:
            end = start
            days = abs(days)
        for n in range(1, days+1):
            new_date = end - datetime.timedelta(days=n)
            dates.append(new_date.strftime(date_format))
    return dates


def get_timeline_slice(timeline, dates_list):
    """Return a partial timeline including only a predefined list of dates."""
    sliced_data = [
        dated_data for dated_data in timeline
        if dated_data['timestamp'][:10] in dates_list
        ]
    return sliced_data


def get_json_slice(timeline, from_date, to_date):
    """Return a partial JSON timeline."""
    dates = get_days(from_date, to_date)
    full_data = json.loads(timeline)
    partial_data = get_timeline_slice(full_data['timeline'], dates)
    full_data['timeline'] = partial_data
    return json.dumps(full_data)


