# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from schedules import get_schedules
from falcon import HTTPNotFound
from oncall.bin.scheduler import load_scheduler


def on_get(req, resp, schedule_id):
    """
    Run the scheduler on demand from a given point in time. Unlike populate it doen't permanently delete or insert anything.
    """
    start_time = float(req.get_param('start', required=True))
    table_name = 'temp_event'

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

    start__lt = req.get_param('start__lt', required=True)
    end__ge = req.get_param('end__ge', required=True)
    team__eq = req.get_param('team__eq', required=True)
    roster_id = schedule['roster_id']

    # create a temporary table with the events that include members of the team's roster
    query = '''
            CREATE TEMPORARY TABLE IF NOT EXISTS `temp_event` AS
            (SELECT `event`.`id`, `event`.`team_id`, `event`.`role_id`, `event`.`schedule_id`, `event`.`link_id`, `event`.`user_id`, `event`.`start`, `event`.`end`, `event`.`note`
            FROM `event`
            INNER JOIN `roster_user`
            ON `event`.`user_id`=`roster_user`.`user_id`
            WHERE `roster_user`.`roster_id`=%s)
        '''

    cursor.execute(query, roster_id)

    scheduler.populate(schedule, start_time, (connection, cursor), table_name)
    resp.body = scheduler.build_preview_response(cursor, start__lt, end__ge, team__eq, table_name)
    cursor.close()
    connection.close()
