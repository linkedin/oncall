# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...utils import load_json_body
from ...auth import check_team_auth, login_required
from .schedules import get_schedules
from falcon import HTTPNotFound
from oncall.bin.scheduler import load_scheduler


@login_required
def on_post(req, resp, schedule_id):
    """
    Run the scheduler on demand from a given point in time. Deletes existing schedule events if applicable.
    Given the ``start`` param, this will find the first schedule start time after ``start``, then populate out
    to the schedule's auto_populate_threshold. It will also clear the calendar of any events associated
    with the chosen schedule from the start of the first event it created onward. For example, if `start`
    is Monday, May 1 and the chosen schedule starts on Wednesday, this will create events starting from
    Wednesday, May 3, and delete any events that start after May 3 that are associated with the schedule.

    **Example request:**

    .. sourcecode:: http

        POST api/v0/   HTTP/1.1
        Content-Type: application/json

    :statuscode 200: Successful populate
    :statuscode 400: Validation checks failed
    """
    # TODO: add images to docstring because it doesn't make sense
    data = load_json_body(req)
    start_time = data['start']

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
    scheduler.populate(schedule, start_time, (connection, cursor))
    cursor.close()
    connection.close()
