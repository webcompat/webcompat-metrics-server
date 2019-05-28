#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Configuration for Ochazuke."""

import os


class Config:
    """Set Flask configuration vars from .env file."""

    # General
    TESTING = False
    FLASK_DEBUG = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    """Special class for testing purpose"""
    SECRET_KEY = 'dev'
    TESTING = True
    FLASK_DEBUG = True
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

app_config = {
    'development': TestConfig,
    'testing': TestConfig,
    'production': Config,
}