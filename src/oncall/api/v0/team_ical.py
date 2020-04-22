# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from . import ical
from .roles import get_role_ids
from ... import db


def get_team_events(team, start, roles=None, include_subscribed=False):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    role_condition = ''
    role_ids = get_role_ids(cursor, roles)
    if role_ids:
        role_condition = ' AND `event`.`role_id` IN ({0})'.format(
            ','.join(map(str, role_ids)))

    team_condition = "`team`.`name` = %s"
    if include_subscribed:
        cursor.execute(
            '''
            SELECT `subscription_id`, `role_id`
            FROM `team_subscription`
            JOIN `team` ON `team_id` = `team`.`id`
            WHERE `team`.`name` = %s
            ''', team)
        if cursor.rowcount != 0:
            subscriptions = ' OR '.join(['(`team`.`id` = %s AND `role`.`id` = %s)' %
                                         (row['subscription_id'], row['role_id'])
                                         for row in cursor])
            team_condition = '(%s OR (%s))' % (team_condition, subscriptions)

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
        ''' + team_condition + role_condition

    cursor.execute(query, (start, team))

    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return events


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
    contact = req.get_param_as_bool('contact')
    if contact is None:
        contact = True
    roles = req.get_param_as_list('roles')
    include_sub = req.get_param_as_bool('include_subscribed')
    if include_sub is None:
        include_sub = True

    events = get_team_events(team, start, roles=roles, include_subscribed=include_sub)
    resp.body = ical.events_to_ical(events, team, contact)
    resp.set_header('Content-Type', 'text/calendar')
