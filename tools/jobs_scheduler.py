#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Scheduler for background jobs when we need to gather data."""

from apscheduler.schedulers.blocking import BlockingScheduler

from tools.jobs_tasks import update_timeline

sched = BlockingScheduler()


@sched.scheduled_job('interval', minutes=60)
def needsdiagnosis_job():
    """Create a job for fetching needs_diagnosis total."""
    update_timeline('needsdiagnosis')


sched.start()
