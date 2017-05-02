# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote
from falcon import HTTPError, HTTP_201, HTTPBadRequest
from ujson import dumps as json_dumps

from ...auth import login_required, check_team_auth
from .users import get_user_data
from ... import db
from ...utils import load_json_body, subscribe_notifications, create_audit
from ...constants import ROSTER_USER_ADDED


def on_get(req, resp, team, roster):
    """
    Get all users for a team roster
    """
    team, roster = unquote(team), unquote(roster)
    connection = db.connect()
    cursor = connection.cursor()
    query = '''SELECT `user`.`name` FROM `user`
               JOIN `roster_user` ON `roster_user`.`user_id`=`user`.`id`
               JOIN `roster` ON `roster`.`id`=`roster_user`.`roster_id`
               JOIN `team` ON `team`.`id`=`roster`.`team_id`
               WHERE `roster`.`name`=%s AND `team`.`name`=%s'''
    if req.get_param_as_bool('in_rotation'):
        query += ' AND `roster_user`.`in_rotation` = 1'
    cursor.execute(query, (roster, team))
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp, team, roster):
    """
    Add user to a roster for a team
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
                      UNION
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
        cursor.execute('''INSERT INTO `roster_user` (`user_id`, `roster_id`, `in_rotation`)
                          VALUES (
                              %r,
                              (SELECT `roster`.`id` FROM `roster`
                               JOIN `team` ON `team`.`id`=`roster`.`team_id`
                               WHERE `team`.`name`=%s AND `roster`.`name`=%s),
                               %s
                          )''',
                       (user_id, team, roster, in_rotation))
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
