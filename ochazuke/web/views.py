#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Routes for humans on Ochazuke app."""

from ochazuke.web import web_blueprint


# A route for starting
@web_blueprint.route('/')
def index():
    """Home page of the site"""
    return 'Welcome to ochazuke'
