# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
from falcon import HTTPError, HTTP_201, HTTPBadRequest, HTTPNotFound
from ujson import dumps as json_dumps

from ...auth import login_required, check_team_auth
from .users import get_user_data
from ... import db
from ...utils import load_json_body, subscribe_notifications, create_audit
from ...constants import ROSTER_USER_ADDED


def on_get(req, resp, team, roster):
    """
    Get all users for a team's roster

    **Example request**:

    .. sourcecode:: http

        GET /api/v0/teams/team-foo/rosters/roster-foo/users  HTTP/1.1
        Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        ["jdoe", "asmith"]
    """
    team, roster = unquote(team), unquote(roster)
    connection = db.connect()
    cursor = connection.cursor()
    query = '''SELECT `user`.`name` FROM `user`
               JOIN `roster_user` ON `roster_user`.`user_id`=`user`.`id`
               JOIN `roster` ON `roster`.`id`=`roster_user`.`roster_id`
               JOIN `team` ON `team`.`id`=`roster`.`team_id`
               WHERE `roster`.`name`=%s AND `team`.`name`=%s'''
    in_rotation = req.get_param_as_bool('in_rotation')
    query_params = [roster, team]
    if in_rotation is not None:
        query += ' AND `roster_user`.`in_rotation` = %s'
        query_params.append(in_rotation)
    cursor.execute(query, query_params)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp, team, roster):
    """
    Add user to a roster for a team. On successful creation, returns that user's information.
    This includes id, contacts, etc, similar to the /api/v0/users GET endpoint.


    **Example request:**

    .. sourcecode:: http

        POST /v0/teams/team-foo/rosters/roster-foo/users   HTTP/1.1
        Content-Type: application/json

        {
            "name": "jdoe"
        }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "active": 1,
            "contacts": {
                "email": "jdoe@example.com",
                "im": "jdoe",
                "sms": "+1 111-111-1111",
                "call": "+1 111-111-1111"
            },
            "full_name": "John Doe",
            "id": 1,
            "name": "jdoe",
            "photo_url": "example.image.com",
            "time_zone": "US/Pacific"
        }

    :statuscode 201: Roster user added
    :statuscode 400: Missing "name" parameter
    :statuscode 422: Invalid team/user or user is already in roster.

    """
    team, roster = unquote(team), unquote(roster)
    data = load_json_body(req)

    user_name = data.get('name')
    in_rotation = int(data.get('in_rotation', True))
    if not user_name:
        raise HTTPBadRequest('incomplete data', 'missing field "name"')
    check_team_auth(team, req)

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''(SELECT `id` FROM `team` WHERE `name`=%s)
                      UNION ALL
                      (SELECT `id` FROM `user` WHERE `name`=%s)''', (team, user_name))
    results = [r[0] for r in cursor]
    if len(results) < 2:
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', 'invalid team or user')

    # TODO: validate roster
    (team_id, user_id) = results
    try:
        # also make sure user is in the team
        cursor.execute('''INSERT IGNORE INTO `team_user` (`team_id`, `user_id`) VALUES (%r, %r)''',
                       (team_id, user_id))
        cursor.execute('''SELECT `roster`.`id`, COALESCE(MAX(`roster_user`.`roster_priority`), -1) + 1
                          FROM `roster`
                          LEFT JOIN `roster_user` ON `roster`.`id` = `roster_id`
                          JOIN `team` ON `team`.`id`=`roster`.`team_id`
                          WHERE `team`.`name`=%s AND `roster`.`name`=%s''',
                       (team, roster))
        if cursor.rowcount == 0:
            raise HTTPNotFound()
        roster_id, roster_priority = cursor.fetchone()
        cursor.execute('''INSERT INTO `roster_user` (`user_id`, `roster_id`, `in_rotation`, `roster_priority`)
                          VALUES (
                              %s,
                              %s,
                              %s,
                              %s
                          )''',
                       (user_id, roster_id, in_rotation, roster_priority))
        cursor.execute('''INSERT INTO `schedule_order`
                          SELECT `schedule_id`, %s, COALESCE(MAX(`schedule_order`.`priority`), -1) + 1
                          FROM `schedule_order`
                          JOIN `schedule` ON `schedule`.`id` = `schedule_order`.`schedule_id`
                          JOIN `roster` ON `roster`.`id` = `schedule`.`roster_id`
                          JOIN `team` ON `roster`.`team_id` = `team`.`id`
                          WHERE `roster`.`name` = %s AND `team`.`name` = %s
                          GROUP BY `schedule_id`''',
                       (user_id, roster, team))
        # subscribe user to notifications
        subscribe_notifications(team, user_name, cursor)

        create_audit({'roster': roster, 'user': user_name, 'request_body': data}, team,
                     ROSTER_USER_ADDED, req, cursor)
        connection.commit()
    except db.IntegrityError:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'user "%(name)s" is already in the roster' % data)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps(get_user_data(None, {'name': user_name})[0])
