# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTP_201, HTTPError, HTTPBadRequest
import time

from ujson import dumps as json_dumps
from ... import db, constants
from ...utils import (
    load_json_body, gen_link_id, user_in_team_by_name
)
from ...auth import login_required, check_calendar_auth


@login_required
def on_post(req, resp):
    """
    Endpoint for creating linked events. Responds with event ids for created events.
    Linked events can be swapped in a group, and users are reminded only on the first event of a
    linked series. Linked events have a link_id attribute containing a uuid. All events
    with an equivalent link_id are considered "linked together" in a single set. Editing any single event
    in the set will break the link for that event, clearing the link_id field. Otherwise, linked events behave
    the same as any non-linked event.

    **Example request:**

    .. sourcecode:: http



        POST /api/v0/events/link HTTP/1.1
        Content-Type: application/json

        [
            {
                "start": 1493667700,
                "end": 149368700,
                "user": "jdoe",
                "team": "team-foo",
                "role": "primary",
            },
            {
                "start": 1493677700,
                "end": 149387700,
                "user": "jdoe",
                "team": "team-foo",
                "role": "primary",
            }
        ]

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

        {
            "link_id": "123456789abcdef0123456789abcdef0",
            "event_ids": [1, 2]
        }

    :statuscode 201: Event created
    :statuscode 400: Event validation checks failed
    :statuscode 422: Event creation failed: nonexistent role/event/team
    """
    events = load_json_body(req)
    if not isinstance(events, list):
        raise HTTPBadRequest('Invalid argument',
                             'events argument needs to be a list')
    if not events:
        raise HTTPBadRequest('Invalid argument', 'events list cannot be empty')

    now = time.time()
    team = events[0].get('team')
    if not team:
        raise HTTPBadRequest('Invalid argument',
                             'event missing team attribute')
    check_calendar_auth(team, req)

    event_values = []
    link_id = gen_link_id()

    connection = db.connect()
    cursor = connection.cursor()

    columns = ('`start`', '`end`', '`user_id`', '`team_id`', '`role_id`', '`link_id`, `note`')

    try:
        cursor.execute('SELECT `id` FROM `team` WHERE `name`=%s', team)
        team_id = cursor.fetchone()
        if not team_id:
            raise HTTPBadRequest('Invalid event',
                                 'Invalid team name: %s' % team)

        values = [
            '%s',
            '%s',
            '(SELECT `id` FROM `user` WHERE `name`=%s)',
            '%s',
            '(SELECT `id` FROM `role` WHERE `name`=%s)',
            '%s',
            '%s'
        ]

        for ev in events:
            if ev['start'] < now - constants.GRACE_PERIOD:
                raise HTTPBadRequest('Invalid event',
                                     'Creating events in the past not allowed')
            if ev['start'] >= ev['end']:
                raise HTTPBadRequest('Invalid event',
                                     'Event must start before it ends')
            ev_team = ev.get('team')
            if not ev_team:
                raise HTTPBadRequest('Invalid event', 'Missing team for event')
            if team != ev_team:
                raise HTTPBadRequest('Invalid event', 'Events can only be submitted to one team')
            if not user_in_team_by_name(cursor, ev['user'], team):
                raise HTTPBadRequest('Invalid event',
                                     'User %s must be part of the team %s' % (ev['user'], team))
            event_values.append((ev['start'], ev['end'], ev['user'], team_id, ev['role'], link_id, ev.get('note')))

        insert_query = 'INSERT INTO `event` (%s) VALUES (%s)' % (','.join(columns), ','.join(values))
        cursor.executemany(insert_query, event_values)
        connection.commit()
        cursor.execute('SELECT `id` FROM `event` WHERE `link_id`=%s ORDER BY `start`', link_id)
        ev_ids = [row[0] for row in cursor]
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'role_id\' cannot be null':
            err_msg = 'role not found'
        elif err_msg == 'Column \'user_id\' cannot be null':
            err_msg = 'user not found'
        elif err_msg == 'Column \'team_id\' cannot be null':
            err_msg = 'team "%s" not found' % team
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps({'link_id': link_id, 'event_ids': ev_ids})
