#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Create Ochazuke: the webcompat-metrics-server Flask application."""

import os
import logging
import json

from flask import Flask
from flask import request
from flask import Response

from ochazuke.helpers import get_json_slice
from ochazuke.helpers import is_valid_args
from ochazuke.helpers import normalize_date_range
from tools.helpers import get_remote_data
from ochazuke.models import db
from ochazuke.models import IssuesCount


def create_app(test_config=None):
    """Create the main webcompat metrics server app."""
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # configure the postgresql database
    if test_config is None:
        # fetch the environment variables for the database and hook secret
        database_url = os.environ.get('DATABASE_URL')
    else:
        # use the local database for testing and a dummy secret
        database_url = 'postgresql://localhost/metrics'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # A route for starting
    @app.route('/')
    def index():
        """Home page of the site"""
        return 'Welcome to ochazuke'

    @app.route('/data/needsdiagnosis-timeline')
    def needsdiagnosis_data():
        """Dumb pipeline for returning the JSON."""
        # TODO: Change this to a local file.
        json_data = get_remote_data(
            'http://www.la-grange.net/tmp/needsdiagnosis-timeline.json')
        if is_valid_args(request.args):
            json_data = get_json_slice(
                json_data,
                request.args.get('from'),
                request.args.get('to')
            )
        response = Response(
            response=json_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/weekly-counts')
    def weekly_reports_data():
        """Secondhand pipeline for returning weekly JSON data."""
        json_weekly_data = get_remote_data(
            'http://laghee.pythonanywhere.com/tmp/weekly_issues')
        if is_valid_args(request.args):
            json_weekly_data = get_json_slice(
                json_weekly_data,
                request.args.get('from'),
                request.args.get('to')
            )
        response = Response(
            response=json_weekly_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/needsdiagnosis-dbtest')
    def needsdiagnosis_from_db():
        """Test route that queries database to serve data to client."""
        if is_valid_args(request.args):
            date_pair = normalize_date_range(
                request.args.get('from'), request.args.get('to'))
            needsdiagnosis_data = IssuesCount.query.filter_by(
                milestone='needsdiagnosis').filter(
                    IssuesCount.timestamp.between(
                        date_pair[0], date_pair[1])).all()
            timeline = []
            for item in needsdiagnosis_data:
                hourly_count = dict(
                    timestamp=item.timestamp.isoformat()+'Z',
                    count=item.count)
                timeline.append(hourly_count)
            response_object = {
                'about': 'Hourly NeedsDiagnosis issues count',
                'date_format': 'w3c',
                'timeline': timeline
            }
            response = Response(
                response=json.dumps(response_object),
                status=200,
                mimetype='application/json')
        else:
            response = Response(status=400)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/needstriage-timeline')
    def needstriage_data():
        """Dumb pipeline for returning the JSON."""
        # TODO: Change this to a database query.
        json_data = get_remote_data(
            'http://laghee.pythonanywhere.com/tmp/needstriage_timeline')
        if is_valid_args(request.args):
            json_data = get_json_slice(
                json_data,
                request.args.get('from'),
                request.args.get('to')
            )
        response = Response(
            response=json_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/needscontact-timeline')
    def needscontact_data():
        """Dumb pipeline for returning the JSON."""
        # TODO: Change this to a database query.
        json_data = get_remote_data(
            'http://laghee.pythonanywhere.com/tmp/needscontact_timeline')
        if is_valid_args(request.args):
            json_data = get_json_slice(
                json_data,
                request.args.get('from'),
                request.args.get('to')
            )
        response = Response(
            response=json_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/sitewait-timeline')
    def sitewait_data():
        """Dumb pipeline for returning the JSON."""
        # TODO: Change this to a database query.
        json_data = get_remote_data(
            'http://laghee.pythonanywhere.com/tmp/sitewait_timeline')
        if is_valid_args(request.args):
            json_data = get_json_slice(
                json_data,
                request.args.get('from'),
                request.args.get('to')
            )
        response = Response(
            response=json_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    @app.route('/data/triage-bugs')
    def triage_bugs():
        """Returns the list of issues which are currently in triage."""
        url = 'https://api.github.com/repos/webcompat/web-bugs/issues?sort=created&per_page=100&direction=asc&milestone=2'  # noqa
        json_data = get_remote_data(url)
        response = Response(
            response=json_data,
            status=200,
            mimetype='application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Vary', 'Origin')
        return response

    return app


# Logging Capabilities
# To benefit from the logging, you may want to add:
#   app.logger.info(Thing_To_Log)
# it will create a line with the following format
# (2015-09-14 20:50:19) INFO: Thing_To_Log
logging.basicConfig(format='(%(asctime)s) %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d  %H:%M:%S %z', level=logging.INFO)

app = create_app()
