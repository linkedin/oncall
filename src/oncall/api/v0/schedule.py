# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPBadRequest, HTTPForbidden

from ...auth import login_required, check_team_auth
from .schedules import insert_schedule_events
from ... import db
from ...utils import load_json_body
from json import dumps as json_dumps
from .schedules import validate_simple_schedule, get_schedules

columns = {
    'role': '`role_id`=(SELECT `id` FROM `role` WHERE `name`=%(role)s)',
    'team': '`team_id`=(SELECT `id` FROM `team` WHERE `name`=%(team)s)',
    'roster': '`roster_id`=(SELECT `roster`.`id` FROM `roster` JOIN `team` ON `roster`.`team_id` = `team`.`id` '
              'WHERE `roster`.`name`=%(roster)s AND `team`.`name`=%(team)s)',
    'auto_populate_threshold': '`auto_populate_threshold`=%(auto_populate_threshold)s',
    'advanced_mode': '`advanced_mode` = %(advanced_mode)s',
    'scheduler': '`scheduler_id`=(SELECT `id` FROM `scheduler` WHERE `name` = %(scheduler)s)'
}


def verify_auth(req, schedule_id, connection, cursor):
    team_query = ('SELECT `team`.`name` FROM `schedule` JOIN `team` '
                  'ON `schedule`.`team_id` = `team`.`id` WHERE `schedule`.`id` = %s')
    cursor.execute(team_query, schedule_id)
    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        raise HTTPNotFound()
    try:
        check_team_auth(cursor.fetchone()[0], req)
    except HTTPForbidden:
        cursor.close()
        connection.close()
        raise


def on_get(req, resp, schedule_id):
    """
    Get schedule information. Detailed information on schedule parameters is provided in the
    POST method for /api/v0/team/{team_name}/rosters/{roster_name}/schedules.

    **Example request**:

    .. sourcecode:: http

        GET /api/v0/schedules/1234  HTTP/1.1
        Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

            {
                "advanced_mode": 1,
                "auto_populate_threshold": 30,
                "events": [
                    {
                        "duration": 259200,
                        "start": 0
                    }
                ],
                "id": 1234,
                "role": "primary",
                "role_id": 1,
                "roster": "roster-foo",
                "roster_id": 2922,
                "team": "asdf",
                "team_id": 2121,
                "timezone": "US/Pacific"
            }
    """

    resp.body = json_dumps(get_schedules({'id': schedule_id}, fields=req.get_param_as_list('fields'))[0])


@login_required
def on_put(req, resp, schedule_id):
    """
    Update a schedule. Allows editing of role, team, roster, auto_populate_threshold,
    events, and advanced_mode. Only allowed for team admins. Note that simple mode
    schedules must conform to simple schedule restrictions (described in documentation
    for the /api/v0/team/{team_name}/rosters/{roster_name}/schedules GET endpoint).
    This is checked on both "events" and "advanced_mode" edits.

    **Example request:**

    .. sourcecode:: http

        PUT /api/v0/schedules/1234 HTTP/1.1
        Content-Type: application/json

        {
            "role": "primary",
            "team": "team-bar",
            "roster": "roster-bar",
            "auto_populate_threshold": 28,
            "events":
                [
                    {
                        "start": 0,
                        "duration": 100
                    }
                ]
            "advanced_mode": 1
        }
    """
    data = load_json_body(req)

    # Get rid of extraneous column data (so pymysql doesn't try to escape it)
    events = data.pop('events', None)
    scheduler = data.pop('scheduler', None)
    if scheduler:
        data['scheduler'] = scheduler['name']
    data = dict((k, data[k]) for k in data if k in columns)
    if 'roster' in data and 'team' not in data:
        raise HTTPBadRequest('Invalid edit', 'team must be specified with roster')
    cols = ', '.join(columns[col] for col in data)

    update = 'UPDATE `schedule` SET ' + cols + ' WHERE `id`=%d' % int(schedule_id)
    connection = db.connect()
    cursor = connection.cursor()
    verify_auth(req, schedule_id, connection, cursor)

    # Validate simple schedule events
    if events:
        simple = validate_simple_schedule(events)
    else:
        cursor.execute('SELECT duration FROM schedule_event WHERE schedule_id = %s', schedule_id)
        existing_events = [{'duration': row[0]} for row in cursor.fetchall()]
        simple = validate_simple_schedule(existing_events)

    # Get advanced mode value (existing or new)
    advanced_mode = data.get('advanced_mode')
    if advanced_mode is None:
        cursor.execute('SELECT advanced_mode FROM schedule WHERE id = %s', schedule_id)
        advanced_mode = cursor.fetchone()[0]
    # if advanced mode is 0 and the events cannot exist as a simple schedule, raise an error
    if not advanced_mode and not simple:
        raise HTTPBadRequest('Invalid edit', 'schedule cannot be represented in simple mode')

    if cols:
        cursor.execute(update, data)
    if events:
        cursor.execute('DELETE FROM `schedule_event` WHERE `schedule_id` = %s', schedule_id)
        insert_schedule_events(schedule_id, events, cursor)
    if scheduler and scheduler['name'] == 'round-robin':
        params = [(schedule_id, name, idx) for idx, name in enumerate(scheduler.get('data'))]
        cursor.execute('DELETE FROM `schedule_order` WHERE `schedule_id` = %s', schedule_id)
        cursor.executemany('''INSERT INTO `schedule_order` (`schedule_id`, `user_id`, `priority`)
                              VALUES (%s, (SELECT `id` FROM `user` WHERE `name` = %s), %s)''',
                           params)
    connection.commit()
    cursor.close()
    connection.close()


@login_required
def on_delete(req, resp, schedule_id):
    """
    Delete a schedule by id. Only allowed for team admins.

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/schedules/1234 HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: Schedule not found
    """
    connection = db.connect()
    cursor = connection.cursor()
    verify_auth(req, schedule_id, connection, cursor)
    cursor.execute('DELETE FROM `schedule` WHERE `id`=%s', int(schedule_id))
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()

    if deleted == 0:
        raise HTTPNotFound()
