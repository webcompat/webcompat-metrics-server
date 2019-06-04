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

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Special class for development purpose"""
    # export FLASK_ENV=development
    # on your local computer
    DEBUG = True
    # Database
    SQLALCHEMY_DATABASE_URL = os.environ.get('DEV_DATABASE_URL')


class TestingConfig(Config):
    """Special class for testing purpose"""
    TESTING = True
    DEBUG = True
    FLASK_DEBUG = True
    # Database
    SQLALCHEMY_DATABASE_URL = os.environ.get('TEST_DATABASE_URL') or 'sqlite://'  # noqa
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    """Production Ready Config."""
    SQLALCHEMY_DATABASE_URL = os.environ.get('DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    # Secure Fallback
    'default': DevelopmentConfig,
}
