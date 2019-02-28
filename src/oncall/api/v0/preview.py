# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from .schedules import get_schedules
from falcon import HTTPNotFound
from oncall.bin.scheduler import load_scheduler
import operator


def on_get(req, resp, schedule_id):
    """
    Run the scheduler on demand from a given point in time. Unlike populate it doen't permanently delete or insert anything.
    """
    start_time = float(req.get_param('start', required=True))
    start__lt = req.get_param('start__lt', required=True)
    end__ge = req.get_param('end__ge', required=True)
    team__eq = req.get_param('team__eq', required=True)
    last_end = 0
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
    team_id = schedule['team_id']

    # get earliest relevant end time
    query = '''
            SELECT `user_id`, MAX(`end`) AS `last_end` FROM `event`
            WHERE (`team_id` = %s OR `team_id` IN (SELECT `subscription_id` FROM team_subscription WHERE `team_id` = %s)) AND `end` <= %s
            GROUP BY `user_id`
            '''

    cursor.execute(query, (team_id, team_id, start_time))
    if cursor.rowcount != 0:
        last_end = min(cursor.fetchall(), key=operator.itemgetter('last_end'))['last_end']

    # create a temporary table with the events that include members of the team's rosters and subscriptions
    query = '''
        CREATE TEMPORARY TABLE `temp_event` AS
        (SELECT DISTINCT `event`.`id`, `event`.`team_id`, `event`.`role_id`,
        `event`.`schedule_id`, `event`.`link_id`, `event`.`user_id`,
        `event`.`start`, `event`.`end`, `event`.`note`
        FROM `event`
        INNER JOIN `roster_user`
        ON `event`.`user_id`=`roster_user`.`user_id`
        WHERE `roster_user`.`roster_id` IN
        (SELECT `id` FROM `roster` WHERE (`team_id` = %s OR `team_id` IN (SELECT `subscription_id` FROM team_subscription WHERE `team_id` = %s)))
        AND `event`.`end` >= %s)
    '''

    cursor.execute(query, (team_id, team_id, last_end))

    scheduler.populate(schedule, start_time, (connection, cursor), table_name)
    resp.body = scheduler.build_preview_response(cursor, start__lt, end__ge, team__eq, table_name)
    cursor.execute("DROP TEMPORARY TABLE `temp_event`")
    cursor.close()
    connection.close()
