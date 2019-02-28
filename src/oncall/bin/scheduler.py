#!/usr/bin/env python

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# -*- coding:utf-8 -*-
import sys
import time
import importlib
from collections import defaultdict

from oncall import db, utils
from oncall.api.v0.schedules import get_schedules

import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-6s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

logging.getLogger('requests').setLevel(logging.WARN)


def load_scheduler(scheduler_name):
    return importlib.import_module('oncall.scheduler.' + scheduler_name).Scheduler()


def main():
    config = utils.read_config(sys.argv[1])
    db.init(config['db'])

    cycle_time = config.get('scheduler_cycle_time', 3600)
    schedulers = {}

    while 1:
        connection = db.connect()
        db_cursor = connection.cursor(db.DictCursor)

        start = time.time()
        # Load all schedulers
        db_cursor.execute('SELECT name FROM scheduler')
        schedulers = {}
        for row in db_cursor:
            try:
                scheduler_name = row['name']
                if scheduler_name not in schedulers:
                    schedulers[scheduler_name] = load_scheduler(scheduler_name)
            except (ImportError, AttributeError):
                logger.exception('Failed to load scheduler %s, skipping', row['name'])

        # Iterate through all teams
        db_cursor.execute('SELECT id, name, scheduling_timezone FROM team WHERE active = TRUE')
        teams = db_cursor.fetchall()
        for team in teams:
            logger.info('scheduling for team: %s', team['name'])
            schedule_map = defaultdict(list)
            for schedule in get_schedules({'team_id': team['id']}):
                schedule_map[schedule['scheduler']['name']].append(schedule)

            for scheduler_name, schedules in schedule_map.items():
                schedulers[scheduler_name].schedule(team, schedules, (connection, db_cursor))

        # Sleep until next time
        sleep_time = cycle_time - (time.time() - start)
        if sleep_time > 0:
            logger.info('Sleeping for %s seconds' % sleep_time)
            time.sleep(cycle_time - (time.time() - start))
        else:
            logger.info('Schedule loop took %s seconds, skipping sleep' % (time.time() - start))

        db_cursor.close()
        connection.close()


if __name__ == '__main__':
    main()
