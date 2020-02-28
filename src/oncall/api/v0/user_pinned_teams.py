# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...utils import load_json_body
from ...auth import login_required, check_user_auth
from ujson import dumps as json_dumps
from falcon import HTTPBadRequest, HTTP_201, HTTPError


def on_get(req, resp, user_name):
    '''
    Get all pinned team names for a user

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users/jdoe/pinned_teams HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "team-foo"
        ]
    '''
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''SELECT `team`.`name`
                      FROM `pinned_team` JOIN `team` ON `pinned_team`.`team_id` = `team`.`id`
                      WHERE `pinned_team`.`user_id` = (SELECT `id` FROM `user` WHERE `name` = %s)''',
                   user_name)
    teams = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(teams)


@login_required
def on_post(req, resp, user_name):
    '''
    Pin a team to the landing page for a user

    **Example request**:

    .. sourcecode:: http

        POST /api/v0/users/jdoe/pinned_teams HTTP/1.1
        Host: example.com

        {
            "team": "team-foo"
        }

    :statuscode 201: Successful team pin
    :statuscode 400: Missing team parameter or team already pinned
    '''
    check_user_auth(user_name, req)
    data = load_json_body(req)
    team = data.get('team')
    if team is None:
        raise HTTPBadRequest('Invalid team pin', 'Missing team parameter')
    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''INSERT INTO `pinned_team` (`user_id`, `team_id`)
                          VALUES ((SELECT `id` FROM `user` WHERE `name` = %s),
                                  (SELECT `id` FROM `team` WHERE `name` = %s))''',
                       (user_name, team))
        connection.commit()
    except db.IntegrityError as e:
        # Duplicate key
        if e.args[0] == 1062:
            raise HTTPBadRequest('Invalid team pin', 'Team already pinned for this user')
        # Team/user is null
        elif e.args[0] == 1048:
            err_msg = str(e.args[1])
            if err_msg == 'Column \'user_id\' cannot be null':
                err_msg = 'user "%s" not found' % user_name
            elif err_msg == 'Column \'team_id\' cannot be null':
                err_msg = 'team "%s" not found' % team
            raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()
    resp.status = HTTP_201
