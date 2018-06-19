#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Create Ochazuke: the webcompat-metrics-server Flask application."""

import os

from flask import Flask
from flask import request
from flask import Response

from ochazuke.helpers import get_json_slice
from ochazuke.helpers import is_valid_args
from tools.helpers import get_remote_data


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
        response.headers.add(
            'Access-Control-Allow-Origin',
            'https://webcompat.github.io')
        response.headers.add(
            'Access-Control-Allow-Credentials',
            'true')
        response.headers.add('Vary', 'Origin')
        return response

    return app


app = create_app()
