# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote

from falcon import HTTPNotFound
from ujson import dumps as json_dumps

from ...auth import login_required, check_team_auth
from ... import db


def on_get(req, resp):
    """
    Get list of team to user mappings

    **Example request**:

    .. sourcecode:: http

        GET /api/v0/team_users  HTTP/1.1
        Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "team": "team1",
                "user" : "jdoe"
            }
        ]
    """
    query = '''SELECT `team`.`name` as team_name, `user`.`name` as user_name FROM `team_user`
                      JOIN `user` ON `team_user`.`user_id`=`user`.`id`
                      JOIN `team` ON `team_user`.`team_id`=`team`.`id`'''
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute(query)
    data = [{'team': r[0], 'user': r[1]} for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_delete(req, resp, team, user):
    """
    Delete user from a team

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/teams/team-foo/users/jdoe HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: User not found in team
    """
    team = unquote(team)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''DELETE FROM `team_user`
                      WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                      AND `user_id`=(SELECT `id` FROM `user` WHERE `name`=%s)''',
                   (team, user))
    deleted = cursor.rowcount
    if deleted == 0:
        raise HTTPNotFound()

    connection.commit()
    cursor.close()
    connection.close()
