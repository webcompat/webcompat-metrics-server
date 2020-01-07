#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Create Ochazuke: the webcompat-metrics-server Flask application."""

import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import config


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name):
    """Create the main webcompat metrics server app."""
    # Create and configure the app
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    # DB init
    db.init_app(app)
    # Migration setup
    migrate.init_app(app, db)
    # Blueprint
    configure_blueprints(app)
    return app


def configure_blueprints(app):
    """Define the blueprints for the project."""
    # Web views for humans
    from ochazuke.web import web_blueprint

    app.register_blueprint(web_blueprint)
    # Views for API clients
    from ochazuke.api import api_blueprint

    app.register_blueprint(api_blueprint, url_prefix="/data")


# Logging Capabilities
# To benefit from the logging, you may want to add:
#   app.logger.info(Thing_To_Log)
# it will create a line with the following format
# (2015-09-14 20:50:19) INFO: Thing_To_Log
logging.basicConfig(
    format="(%(asctime)s) %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d  %H:%M:%S %z",
    level=logging.INFO,
)

application = create_app("development")

if __name__ == "__main__":
    application.run()
