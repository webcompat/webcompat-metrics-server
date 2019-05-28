#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Create Ochazuke: the webcompat-metrics-server Flask application."""

import logging
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(test_config=None):
    """Create the main webcompat metrics server app."""
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_object('config.Config')
    else:
        # load the test config if passed in
        app.config.from_object('config.TestConfig')
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    # Initialize the DB
    db.init_app(app)
    # Start the app context
    with app.app_context():
        from ochazuke import routes  # noqa
        db.create_all()
    return app


# Logging Capabilities
# To benefit from the logging, you may want to add:
#   app.logger.info(Thing_To_Log)
# it will create a line with the following format
# (2015-09-14 20:50:19) INFO: Thing_To_Log
logging.basicConfig(format='(%(asctime)s) %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d  %H:%M:%S %z', level=logging.INFO)

app = create_app()
