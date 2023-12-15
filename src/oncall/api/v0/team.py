# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import uuid
import time
from urllib.parse import unquote
from falcon import HTTPNotFound, HTTPBadRequest, HTTPError
from ujson import dumps as json_dumps

from ... import db, iris
from .users import get_user_data
from .rosters import get_roster_by_team_id
from ...auth import login_required, check_team_auth
from ...utils import load_json_body, invalid_char_reg, create_audit
from ...constants import TEAM_DELETED, TEAM_EDITED, SUPPORTED_TIMEZONES

# Columns which may be modified
cols = set(['name', 'description', 'slack_channel', 'slack_channel_notifications', 'email', 'scheduling_timezone',
            'iris_plan', 'iris_enabled', 'override_phone_number', 'api_managed_roster'])


def populate_team_users(cursor, team_dict):
    cursor.execute('''SELECT `user`.`name` FROM `team_user`
                      JOIN `user` ON `team_user`.`user_id`=`user`.`id`
                      WHERE `team_id`=%s''',
                   team_dict['id'])
    team_dict['users'] = dict((r['name'], get_user_data(None, {'name__eq': r['name']})[0])
                              for r in cursor)


def populate_team_admins(cursor, team_dict):
    cursor.execute('''SELECT `user`.`name` FROM `team_admin`
                      JOIN `user` ON `team_admin`.`user_id`=`user`.`id`
                      WHERE `team_id`=%s''',
                   team_dict['id'])
    team_dict['admins'] = [{'name': r['name']} for r in cursor]


def populate_team_services(cursor, team_dict):
    cursor.execute('''SELECT `service`.`name` FROM `team_service`
                      JOIN `service` ON `team_service`.`service_id`=`service`.`id`
                      WHERE `team_id`=%s''',
                   team_dict['id'])
    team_dict['services'] = [r['name'] for r in cursor]


def populate_team_rosters(cursor, team_dict):
    team_dict['rosters'] = get_roster_by_team_id(cursor, team_dict['id'])


populate_map = {
    'users': populate_team_users,
    'admins': populate_team_admins,
    'services': populate_team_services,
    'rosters': populate_team_rosters
}


def on_get(req, resp, team):
    '''
    Get team info by name. By default, only finds active teams. Allows selection of
    fields, including: users, admins, services, descriptions, and rosters. If no ``fields`` is
    specified in the query string, it defaults to all fields.

    **Example request**

    .. sourcecode:: http

        GET /api/v0/teams/team-foo  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "admins": [
                {
                    "name": "jdoe"
                }
            ],
            "email": "foo@example.com",
            "id": 5501,
            "iris_plan": null,
            "name": "team-foo",
            "description": "this is an important team!",
            "rosters": {
                "roster-foo": {
                    "id": 4186,
                    "schedules": [
                        {
                            "advanced_mode": 0,
                            "auto_populate_threshold": 21,
                            "events": [
                                {
                                    "duration": 604800,
                                    "start": 7200
                                }
                            ],
                            "id": 2222,
                            "role": "primary",
                            "role_id": 1,
                            "roster": "roster-foo",
                            "roster_id": 4186,
                            "team": "team-foo",
                            "team_id": 5501,
                            "timezone": "US/Pacific"
                        }
                    ],
                    "users": [
                        {
                            "in_rotation": true,
                            "name": "jdoe"
                        }
                    ]
                }
            },
            "scheduling_timezone": "US/Pacific",
            "services": [
                "service-foo"
            ],
            "slack_channel": "#foo",
            "users": {
                "jdoe": {
                    "active": 1,
                    "contacts": {
                        "call": "+1 111-111-1111",
                        "email": "jdoe@example.com",
                        "im": "jdoe",
                        "sms": "+1 111-111-1111"
                    },
                    "full_name": "John Doe",
                    "id": 1234,
                    "name": "jdoe",
                    "photo_url": "image.example.com",
                    "time_zone": "US/Pacific"
                }
            }
        }

    '''
    team = unquote(team)
    fields = req.get_param_as_list('fields')
    active = req.get_param('active', default=True)

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('''SELECT `id`, `name`, `email`, `slack_channel`, `slack_channel_notifications`,
                             `scheduling_timezone`, `iris_plan`, `iris_enabled`, `override_phone_number`, `api_managed_roster`, `description`
                      FROM `team` WHERE `name`=%s AND `active` = %s''', (team, active))
    results = cursor.fetchall()
    if not results:
        raise HTTPNotFound()
    [team_info] = results

    if not fields:
        # default to get all data
        fields = populate_map.keys()
    for field in fields:
        populate = populate_map.get(field)
        if not populate:
            continue
        populate(cursor, team_info)

    cursor.close()
    connection.close()
    resp.body = json_dumps(team_info)


@login_required
def on_put(req, resp, team):
    '''
    Edit a team's information. Allows edit of: 'name', 'description', 'slack_channel', 'slack_channel_notifications', 'email', 'scheduling_timezone',
    'iris_plan', 'iris_enabled', 'override_phone_number', 'api_managed_roster'

    **Example request:**

    .. sourcecode:: http

        PUT /api/v0/teams/team-foo HTTP/1.1
        Content-Type: application/json

        {
            "name": "team-bar",
            "slack_channel": "roster-bar",
            "email": 28,
            "scheduling_timezone": "US/Central"
        }

    :statuscode 200: Successful edit
    :statuscode 400: Invalid team name/iris escalation plan
    :statuscode 422: Duplicate team name
    '''
    team = unquote(team)
    check_team_auth(team, req)
    data = load_json_body(req)

    connection = db.connect()
    cursor = connection.cursor()

    data_cols = data.keys()
    if 'name' in data:
        invalid_char = invalid_char_reg.search(data['name'])
        if invalid_char:
            raise HTTPBadRequest('invalid team name',
                                 'team name contains invalid character "%s"' % invalid_char.group())
        elif data['name'] == '':
            raise HTTPBadRequest('invalid team name', 'empty team name')

    if 'iris_plan' in data and data['iris_plan']:
        iris_plan = data['iris_plan']
        plan_resp = iris.client.get(iris.client.url + 'plans?name=%s&active=1' % iris_plan)
        if plan_resp.status_code != 200 or plan_resp.json() == []:
            raise HTTPBadRequest('invalid iris escalation plan', 'no iris plan named %s exists' % iris_plan)
    if 'iris_enabled' in data:
        if not type(data['iris_enabled']) == bool:
            raise HTTPBadRequest('invalid payload', 'iris_enabled must be boolean')
    if 'api_managed_roster' in data:
        if not type(data['api_managed_roster']) == bool:
            raise HTTPBadRequest('invalid payload', 'api_managed_roster must be boolean')
    if 'scheduling_timezone' in data:
        if data['scheduling_timezone'] not in SUPPORTED_TIMEZONES:
            raise HTTPBadRequest('invalid payload', 'requested scheduling_timezone is not supported. Supported timezones: %s' % str(SUPPORTED_TIMEZONES))

    set_clause = ', '.join(['`{0}`=%s'.format(d) for d in data_cols if d in cols])
    query_params = tuple(data[d] for d in data_cols if d in cols) + (team,)
    try:
        update_query = 'UPDATE `team` SET {0} WHERE name=%s'.format(set_clause)
        cursor.execute(update_query, query_params)
        create_audit({'request_body': data}, team, TEAM_EDITED, req, cursor)
        connection.commit()
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if 'Duplicate entry' in err_msg:
            err_msg = "A team named '%s' already exists" % (data['name'])
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()


@login_required
def on_delete(req, resp, team):
    '''
    Soft delete for teams. Does not remove data from the database, but sets the team's active
    param to false. Note that this means deleted teams' names remain in the namespace, so new
    teams cannot be created with the same name a sa deleted team.

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/teams/team-foo HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: Team not found
    '''
    team = unquote(team)
    new_team = str(uuid.uuid4())
    deletion_date = time.time()
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()
    # Soft delete: set team inactive, delete future events for it
    cursor.execute('UPDATE `team` SET `active` = FALSE WHERE `name`=%s', team)
    cursor.execute('DELETE FROM `event` WHERE `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s) '
                   'AND `start` > UNIX_TIMESTAMP()', team)
    create_audit({}, team, TEAM_DELETED, req, cursor)
    deleted = cursor.rowcount

    if deleted == 0:
        connection.commit()
        cursor.close()
        connection.close()
        raise HTTPNotFound()

    cursor.execute('SELECT `id` FROM `team` WHERE `name`=%s', team)
    team_id = cursor.fetchone()

    # create entry in deleted_teams and then change name in team to preserve a clean namespace
    cursor.execute('UPDATE `team` SET `name` = %s WHERE `name`= %s', (new_team, team))
    cursor.execute('INSERT INTO `deleted_team` (team_id, new_name, old_name, deletion_date) VALUES (%s, %s, %s, %s)', (team_id, new_team, team, deletion_date))
    connection.commit()
    cursor.close()
    connection.close()
