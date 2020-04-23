# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from . import ical
from .roles import get_role_ids
from ... import db


def get_user_events(user_name, start, roles=None):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    role_condition = ''
    role_ids = get_role_ids(cursor, roles)
    if role_ids:
        role_condition = ' AND `event`.`role_id` IN ({0})'.format(
            ','.join(map(str, role_ids)))

    query = '''
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
        ''' + role_condition

    cursor.execute(query, (start, user_name))

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
    roles = req.get_param_as_list('roles')

    events = get_user_events(user_name, start, roles=roles)
    resp.body = ical.events_to_ical(events, user_name, contact)
    resp.set_header('Content-Type', 'text/calendar')
