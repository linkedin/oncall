# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPError, HTTP_201
from ujson import dumps as json_dumps
from .users import get_user_data
from ... import db
from ...auth import login_required, check_team_auth
from ...utils import load_json_body

constraints = {'active': '`team`.`active` = %s'}


def on_get(req, resp, team):
    """
    Get list of usernames for all team members. A user is a member of a team when
    he/she is a team admin or a member of one of the team's rosters. Accepts an
    ``active`` parameter in the query string that filters inactive (deleted) teams.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/teams/team-foo/users   HTTP/1.1
        Content-Type: application/json

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "jdoe",
            "asmith"
        ]
    """
    query = '''SELECT `user`.`name` FROM `user`
               JOIN `team_user` ON `team_user`.`user_id`=`user`.`id`
               JOIN `team` ON `team`.`id`=`team_user`.`team_id`
               WHERE `team`.`name`=%s'''
    active = req.get_param('active')
    query_params = [team]
    if active:
        query += ' AND `team`.`active` = %s'
        query_params.append(active)

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute(query, query_params)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp, team):
    """
    Add user to a team. Deprecated; used only for testing purposes.
    """
    check_team_auth(team, req)
    data = load_json_body(req)

    user_name = data.get('name')
    if not user_name:
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', 'name missing for user')

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''INSERT INTO `team_user` (`team_id`, `user_id`)
                          VALUES (
                              (SELECT `id` FROM `team` WHERE `name`=%s),
                              (SELECT `id` FROM `user` WHERE `name`=%s)
                          )''',
                       (team, user_name))
        connection.commit()
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'user_id\' cannot be null':
            err_msg = 'user %s not found' % user_name
        elif err_msg == 'Column \'team_id\' cannot be null':
            err_msg = 'team %s not found' % team
        elif 'Duplicate entry' in err_msg:
            err_msg = 'user name "%s" is already in team %s' % (user_name, team)
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps(get_user_data(None, {'name': user_name})[0])
