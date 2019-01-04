# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from . import ical

from ... import db


def on_get(req, resp, team):
    """
    Get ics file for a given team's on-call events. Gets all events starting
    after the optional "start" parameter, which defaults to the current
    time. If defined, start should be a Unix timestamp in seconds.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/teams/test-team/ical?start=12345 HTTP/1.1
        Content-Type: text/calendar

        BEGIN:VCALENDAR
        ...
    """
    start = req.get_param_as_int('start')
    if start is None:
        start = int(time.time())
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute(
        '''
        SELECT
            `event`.`id`,
            `team`.`name` AS team,
            `user`.`name` AS user,
            `role`.`name` AS role,
            `event`.`start`,
            `event`.`end`
        FROM `event`
            JOIN `team` ON `event`.`team_id` = `team`.`id`
            JOIN `user` ON `event`.`user_id` = `user`.`id`
            JOIN `role` ON `event`.`role_id` = `role`.`id`
        WHERE
            `event`.`start` > %s AND
            `team`.`name` = %s
        ''',
        (start, team))

    events = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = ical.events_to_ical(events, team)
    resp.set_header('Content-Type', 'text/calendar')
