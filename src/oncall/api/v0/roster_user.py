# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
from falcon import HTTPNotFound, HTTPBadRequest, HTTP_200

from ...auth import login_required, check_team_auth
from ...utils import load_json_body, unsubscribe_notifications, create_audit
from ... import db
from ...constants import ROSTER_USER_DELETED, ROSTER_USER_EDITED


@login_required
def on_delete(req, resp, team, roster, user):
    """
    Delete user from roster

    **Example request**:

    .. sourcecode:: http

        DELETE /v0/api/teams/team_foo/rosters/best_coast/users/user1 HTTP/1.1

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        []

    :statuscode 200: no error, user deleted from roster.
    :statuscode 404: roster not found.
    """
    team, roster = unquote(team), unquote(roster)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''SELECT `id` FROM `roster`
                      WHERE `team_id` = (SELECT `id` FROM `team` WHERE name = %s)
                      AND `name` = %s''',
                   (team, roster))
    roster_id = cursor.fetchone()
    if roster_id is None:
        raise HTTPNotFound()
    cursor.execute('''DELETE FROM `roster_user`
                      WHERE `roster_id`= %s
                      AND `user_id`=(SELECT `id` FROM `user` WHERE `name`=%s)''',
                   (roster_id, user))
    cursor.execute('''DELETE `schedule_order` FROM `schedule_order`
                      JOIN `schedule` ON `schedule`.`id` = `schedule_order`.`schedule_id`
                      WHERE `roster_id` = %s
                      AND user_id = (SELECT `id` FROM `user` WHERE `name` = %s)''',
                   (roster_id, user))
    create_audit({'roster': roster, 'user': user}, team, ROSTER_USER_DELETED, req, cursor)

    # Remove user from the team if needed
    query = '''DELETE FROM `team_user`
        WHERE `user_id` = (SELECT `id` FROM `user` WHERE `name`=%s)
            AND `user_id` NOT IN (
                SELECT `roster_user`.`user_id`
                FROM `roster_user` JOIN `roster` ON `roster`.`id` = `roster_user`.`roster_id`
                WHERE team_id = (SELECT `id` FROM `team` WHERE `name`=%s)
                UNION (
                    SELECT `user_id` FROM `team_admin`
                    WHERE `team_id` = (SELECT `id` FROM `team` WHERE `name`=%s)
                )
            )
            AND `team_user`.`team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)'''
    cursor.execute(query, (user, team, team, team))
    if cursor.rowcount != 0:
        unsubscribe_notifications(team, user, cursor)
    connection.commit()
    cursor.close()
    connection.close()
    resp.status = HTTP_200
    resp.body = '[]'


@login_required
def on_put(req, resp, team, roster, user):
    """
    Put a user into/out of rotation within a given roster

    **Example request**:

    .. sourcecode:: http

        PUT /v0/api/teams/team_foo/rosters/best_coast/users/user1 HTTP/1.1
        Content-Type: application/json

        {"in_rotation": false}

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        []

    :statuscode 200: no error, user status udpated.
    :statuscode 400: invalid request, missing field "in_rotation".
    """
    team, roster = unquote(team), unquote(roster)
    check_team_auth(team, req)
    data = load_json_body(req)

    in_rotation = data.get('in_rotation')
    if in_rotation is None:
        raise HTTPBadRequest('incomplete data', 'missing field "in_rotation"')
    in_rotation = int(in_rotation)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''UPDATE `roster_user` SET `in_rotation`=%s
                      WHERE `user_id` = (SELECT `id` FROM `user` WHERE `name`=%s)
                      AND `roster_id` =
                        (SELECT `id` FROM `roster` WHERE `name`=%s
                         AND `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s))''',
                   (in_rotation, user, roster, team))
    create_audit({'user': user, 'roster': roster, 'request_body': data},
                 team,
                 ROSTER_USER_EDITED,
                 req,
                 cursor)
    connection.commit()
    cursor.close()
    connection.close()
    resp.status = HTTP_200
    resp.body = '[]'
