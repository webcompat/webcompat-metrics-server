#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Set of routes for Ochazuke app."""

import json

from flask import abort

# from flask import current_app as app
from flask import request
from flask import Response

from ochazuke.api import api_blueprint
from ochazuke.helpers import get_weekly_data
from ochazuke.helpers import get_timeline_data
from ochazuke.helpers import is_valid_args
from ochazuke.helpers import is_valid_category
from ochazuke.helpers import normalize_date_range
from tools.helpers import get_remote_data


@api_blueprint.route("/weekly-counts")
def weekly_reports_data():
    """Route for weekly bug reports."""
    if not request.args:
        abort(404)
    if not is_valid_args(request.args):
        abort(404)
    # Extract the dates
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    # Adding the extra day for weekly reports isn't necessary, but won't hurt
    start, end = normalize_date_range(from_date, to_date)
    # Fetch the data
    timeline = get_weekly_data(from_date, to_date)
    # Prepare the response
    response_object = {
        "about": "Weekly Count of New Issues Reported",
        "numbering_of_weeks": "ISO calendar",
        "timeline": timeline,
    }
    response = Response(
        response=json.dumps(response_object),
        status=200,
        mimetype="application/json",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Vary", "Origin")
    return response


@api_blueprint.route("/<category>-timeline")
def issues_count_data(category):
    """Route for issues count."""
    if not is_valid_category(category):
        abort(404)
    if not request.args:
        abort(404)
    if not is_valid_args(request.args):
        abort(404)
    # Extract the dates
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    start, end = normalize_date_range(from_date, to_date)
    # Grab the data
    timeline = get_timeline_data(category, start, end)
    # Prepare the response
    about = "Hourly {category} issues count".format(category=category)
    response_object = {
        "about": about,
        "date_format": "w3c",
        "timeline": timeline,
    }
    response = Response(
        response=json.dumps(response_object),
        status=200,
        mimetype="application/json",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Vary", "Origin")
    return response


@api_blueprint.route("/triage-bugs")
def triage_bugs():
    """Returns the list of issues which are currently in triage."""
    url = "https://api.github.com/repos/webcompat/web-bugs/issues?sort=created&per_page=100&direction=asc&milestone=2"  # noqa
    json_data = get_remote_data(url)
    response = Response(
        response=json_data, status=200, mimetype="application/json"
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Vary", "Origin")
    return response


@api_blueprint.route("/tsci-doc")
def tsci_doc():
    """Returns the current ID of the spreadsheet where TSCI is calculated."""
    url = "https://tsci.webcompat.com/currentDoc.json"  # noqa
    json_data = get_remote_data(url)
    response = Response(
        response=json_data, status=200, mimetype="application/json"
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Vary", "Origin")
    return response
