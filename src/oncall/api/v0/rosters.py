# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
from falcon import HTTPError, HTTP_201, HTTPBadRequest
from ujson import dumps as json_dumps
from ...utils import load_json_body, invalid_char_reg, create_audit
from ...constants import ROSTER_CREATED
from ...auth import login_required, check_team_auth
from ... import db
from .schedules import get_schedules

constraints = {
    'name': '`roster`.`name` = %s',
    'name__eq': '`roster`.`name` = %s',
    'name__contains': '`roster`.`name` LIKE CONCAT("%%", %s, "%%")',
    'name__startswith': '`roster`.`name` LIKE CONCAT(%s, "%%")',
    'name__endswith': '`roster`.`name` LIKE CONCAT("%%", %s)',
    'id': '`roster`.`id` = %s',
    'id__eq': '`roster`.`id` = %s',
}


def get_roster_by_team_id(cursor, team_id, params=None):
    # get all rosters for a team
    query = 'SELECT `id`, `name` from `roster`'
    where_params = []
    where_vals = []
    if params:
        for key, val in params.items():
            if key in constraints:
                where_params.append(constraints[key])
                where_vals.append(val)
    where_params.append('`roster`.`team_id`= %s')
    where_vals.append(team_id)
    where_clause = ' WHERE %s' % ' AND '.join(where_params)

    cursor.execute(query + where_clause, where_vals)
    rosters = dict((row['name'], {'users': [], 'schedules': [], 'id': row['id']})
                   for row in cursor)
    # get users for each roster
    query = '''SELECT `roster`.`name` AS `roster`,
                      `user`.`name` AS `user`,
                      `roster_user`.`in_rotation` AS `in_rotation`
               FROM `roster_user`
               JOIN `roster` ON `roster_user`.`roster_id`=`roster`.`id`
               JOIN `user` ON `roster_user`.`user_id`=`user`.`id`'''
    cursor.execute(query + where_clause, where_vals)
    for row in cursor:
        rosters[row['roster']]['users'].append(
            {'name': row['user'], 'in_rotation': bool(row['in_rotation'])})
    # get all schedules for a team
    data = get_schedules({'team_id': team_id})
    for schedule in data:
        if schedule['roster'] in rosters:
            rosters[schedule['roster']]['schedules'].append(schedule)

    return rosters


def on_get(req, resp, team):
    """
    Get roster info for a team. Returns a JSON object with roster names
    as keys, and info as values. This info includes the roster id, any
    schedules associated with the rosters, and roster users (along
    with their status as in/out of rotation).

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/teams/team-foo/rosters  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

            {
                "roster-foo": {
                    "id": 2923,
                    "schedules": [
                        {
                            "advanced_mode": 0,
                            "auto_populate_threshold": 30,
                            "events": [
                                {
                                    "duration": 604800,
                                    "start": 266400
                                }
                            ],
                            "id": 1788,
                            "role": "primary",
                            "role_id": 1,
                            "roster": "roster-foo",
                            "roster_id": 2923,
                            "team": "team-foo",
                            "team_id": 2122,
                            "timezone": "US/Pacific"
                        }
                    ],
                    "users": [
                        {
                            "in_rotation": true,
                            "name": "jdoe"
                        },
                        {
                            "in_rotation": true,
                            "name": "asmith"
                        }
                    ]
                }
            }

    :statuscode 422: Invalid team

    """
    team = unquote(team)
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute('SELECT `id` FROM `team` WHERE `name`=%s', team)
    if cursor.rowcount != 1:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'team "%s" not found' % team)

    team_id = cursor.fetchone()['id']
    rosters = get_roster_by_team_id(cursor, team_id, req.params)

    cursor.close()
    connection.close()
    resp.body = json_dumps(rosters)


@login_required
def on_post(req, resp, team):
    """
    Create a roster for a team

    **Example request:**

    .. sourcecode:: http

        POST /v0/teams/team-foo/rosters  HTTP/1.1
        Content-Type: application/json

        {
            "name": "roster-foo",
        }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json


    :statuscode 201: Succesful roster creation
    :statuscode 422: Invalid character in roster name/Duplicate roster name
    """
    team = unquote(team)
    data = load_json_body(req)

    roster_name = data.get('name')
    if not roster_name:
        raise HTTPBadRequest('name attribute missing from request', '')
    invalid_char = invalid_char_reg.search(roster_name)
    if invalid_char:
        raise HTTPBadRequest('invalid roster name',
                             'roster name contains invalid character "%s"' % invalid_char.group())

    check_team_auth(team, req)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''INSERT INTO `roster` (`name`, `team_id`)
                          VALUES (%s, (SELECT `id` FROM `team` WHERE `name`=%s))''',
                       (roster_name, team))
    except db.IntegrityError:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'roster name "%s" already exists for team %s' % (roster_name, team))
    create_audit({'roster_id': cursor.lastrowid, 'request_body': data}, team, ROSTER_CREATED, req, cursor)
    connection.commit()
    cursor.close()
    connection.close()

    resp.status = HTTP_201
