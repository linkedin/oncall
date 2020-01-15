# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
from falcon import HTTPError, HTTPNotFound, HTTPBadRequest
from ujson import dumps as json_dumps

from ...auth import login_required, check_team_auth
from ... import db
from ...utils import load_json_body, invalid_char_reg
from .schedules import get_schedules
from ...constants import ROSTER_DELETED, ROSTER_EDITED
from ...utils import create_audit


def on_get(req, resp, team, roster):
    """
    Get user and schedule info for a roster

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/teams/foo-sre/rosters HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "Managers": {
           "id": 2730,
           "users": [
             {
               "in_rotation": true,
               "name": "foo"
             }
           ],
           "schedules": [
             {
               "auto_populate_threshold": 0,
               "roster": "Managers",
               "advanced_mode": 0,
               "role": "manager",
               "team": "foo-sre",
               "events": [
                 {
                   "duration": 604800,
                   "start": 367200
                 }
               ],
               "id": 1704
             }
           ]
         }
       }

    :statuscode 200: no error
    """
    team, roster = unquote(team), unquote(roster)
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute('''SELECT `roster`.`id` AS `roster`, `team`.`id` AS `team` FROM `roster`
                      JOIN `team` ON `team`.`id`=`roster`.`team_id`
                      WHERE `team`.`name`=%s AND `roster`.`name`=%s''',
                   (team, roster))
    results = cursor.fetchall()
    if not results:
        raise HTTPNotFound()
    team_id = results[0]['team']
    roster_id = results[0]['roster']
    # get list of users in the roster
    cursor.execute('''SELECT `user`.`name` as `name`,
                             `roster_user`.`in_rotation` AS `in_rotation`,
                             `roster_user`.`roster_priority`
                      FROM `roster_user`
                      JOIN `user` ON `roster_user`.`user_id`=`user`.`id`
                      WHERE `roster_user`.`roster_id`=%s''', roster_id)
    users = [user for user in cursor]
    # get list of schedule in the roster
    schedules = get_schedules({'team_id': team_id}, dbinfo=(connection, cursor))

    cursor.close()
    connection.close()
    resp.body = json_dumps({'users': users, 'schedules': schedules})


@login_required
def on_put(req, resp, team, roster):
    """
    Change roster name. Must have team admin privileges.

        **Example request:**

    .. sourcecode:: http

        PUT /api/v0/teams/team-foo/rosters/roster-foo HTTP/1.1
        Content-Type: application/json

        {
            "name": "roster-bar",
        }

    :statuscode 400: Invalid roster name, disallowed characters
    :statuscode 422: Duplicate roster name for team
    """
    team, roster = unquote(team), unquote(roster)
    data = load_json_body(req)
    name = data.get('name')
    roster_order = data.get('roster_order')
    check_team_auth(team, req)

    if not (name or roster_order):
        raise HTTPBadRequest('invalid roster update', 'missing roster name or order')

    connection = db.connect()
    cursor = connection.cursor()
    try:
        if roster_order:
            cursor.execute('''SELECT `user`.`name` FROM `roster_user`
                              JOIN `roster` ON `roster`.`id` = `roster_user`.`roster_id`
                              JOIN `user` ON `roster_user`.`user_id` = `user`.`id`
                              WHERE `roster_id` = (SELECT id FROM roster WHERE name = %s
                                AND team_id = (SELECT id from team WHERE name = %s))''',
                           (roster, team))
            roster_users = {row[0] for row in cursor}
            if not all([x in roster_users for x in roster_order]):
                raise HTTPBadRequest('Invalid roster order', 'All users in provided order must be part of the roster')
            if not len(roster_order) == len(roster_users):
                raise HTTPBadRequest('Invalid roster order', 'Roster order must include all roster members')

            cursor.executemany('''UPDATE roster_user SET roster_priority = %s
                                  WHERE roster_id = (SELECT id FROM roster WHERE name = %s
                                    AND team_id = (SELECT id FROM team WHERE name = %s))
                                  AND user_id = (SELECT id FROM user WHERE name = %s)''',
                               ((idx, roster, team, user) for idx, user in enumerate(roster_order)))
            connection.commit()

        if name and name != roster:
            invalid_char = invalid_char_reg.search(name)
            if invalid_char:
                raise HTTPBadRequest('invalid roster name',
                                     'roster name contains invalid character "%s"' % invalid_char.group())
            cursor.execute(
                '''UPDATE `roster` SET `name`=%s
                   WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                       AND `name`=%s''',
                (name, team, roster))
            create_audit({'old_name': roster, 'new_name': name}, team, ROSTER_EDITED, req, cursor)
            connection.commit()
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if 'Duplicate entry' in err_msg:
            err_msg = "roster '%s' already existed for team '%s'" % (name, team)
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()


@login_required
def on_delete(req, resp, team, roster):
    """
    Delete roster
    """
    team, roster = unquote(team), unquote(roster)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('SELECT `user_id` FROM `roster_user` JOIN `roster` ON `roster_user`.`roster_id` = `roster`.`id` '
                   'WHERE `roster`.`name` = %s AND `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)',
                   (roster, team))
    user_ids = cursor.fetchall()
    cursor.execute('DELETE FROM `roster_user` WHERE `roster_id` = (SELECT `id` FROM `roster` WHERE `name` = %s '
                   'AND `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s))', (roster, team))

    if user_ids:
        # Remove users from the team if needed
        query = '''DELETE FROM `team_user` WHERE `user_id` IN %s AND `user_id` NOT IN
                       (SELECT `roster_user`.`user_id`
                        FROM `roster_user` JOIN `roster` ON `roster`.`id` = `roster_user`.`roster_id`
                        WHERE team_id = (SELECT `id` FROM `team` WHERE `name`=%s)
                       UNION
                       (SELECT `user_id` FROM `team_admin`
                        WHERE `team_id` = (SELECT `id` FROM `team` WHERE `name`=%s)))
                   AND `team_user`.`team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)'''
        cursor.execute(query, (user_ids, team, team, team))

    cursor.execute('''DELETE FROM `roster`
                      WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                      AND `name`=%s''',
                   (team, roster))
    deleted = cursor.rowcount
    if deleted:
        create_audit({'name': roster}, team, ROSTER_DELETED, req, cursor)

    connection.commit()
    cursor.close()
    connection.close()

    if deleted == 0:
        raise HTTPNotFound()
