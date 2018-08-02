# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...auth import check_team_auth
from schedules import get_schedules
from falcon import HTTPNotFound
from oncall.bin.scheduler import load_scheduler


def on_get(req, resp, schedule_id):
    """
    Run the scheduler on demand from a given point in time. Unlike populate it doen't permanently delete or insert anything.
    """
    table_name = 'temp_event'
    start_time = float(req.get_param('start', required=True))

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('''SELECT `scheduler`.`name` FROM `schedule`
                      JOIN `scheduler` ON `schedule`.`scheduler_id` = `scheduler`.`id`
                      WHERE `schedule`.`id` = %s''',
                   schedule_id)
    if cursor.rowcount == 0:
        raise HTTPNotFound()
    scheduler_name = cursor.fetchone()['name']
    scheduler = load_scheduler(scheduler_name)
    schedule = get_schedules({'id': schedule_id})[0]
    check_team_auth(schedule['team'], req)
    scheduler.populate(schedule, start_time, (connection, cursor), req, resp, table_name)
    cursor.close()
    connection.close()
