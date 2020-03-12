# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from . import ical
from ... import db


def get_user_events(user_name, start):
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
            `event`.`end` > %s AND
            `user`.`name` = %s
        ''',
        (start, user_name))

    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return events


def on_get(req, resp, user_name):
    """
    Get ics file for a given user's on-call events. Gets all events starting
    after the optional "start" parameter, which defaults to the current
    time. If defined, start should be a Unix timestamp in seconds.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/users/jdoe/ical HTTP/1.1
        Content-Type: text/calendar

        BEGIN:VCALENDAR
        ...

    """
    start = req.get_param_as_int('start')
    if start is None:
        start = int(time.time())
    contact = req.get_param_as_bool('contact')
    if contact is None:
        contact = True

    events = get_user_events(user_name, start)
    resp.body = ical.events_to_ical(events, user_name, contact)
    resp.set_header('Content-Type', 'text/calendar')
