# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote
from falcon import HTTPNotFound, HTTPBadRequest, HTTPError
from ujson import dumps as json_dumps

from ... import db, iris
from .users import get_user_data
from .rosters import get_roster_by_team_id
from ...auth import login_required, check_team_auth
from ...utils import load_json_body, invalid_char_reg, create_audit
from ...constants import TEAM_DELETED, TEAM_EDITED


cols = set(['name', 'slack_channel', 'email', 'scheduling_timezone', 'iris_plan'])


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
    team = unquote(team)
    fields = req.get_param_as_list('fields')
    active = req.get_param('active', default=True)

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('SELECT `id`, `name`, `email`, `slack_channel`, `scheduling_timezone`, `iris_plan` '
                   'FROM `team` WHERE `name`=%s AND `active` = %s', (team, active))
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

    if 'iris_plan' in data:
        iris_plan = data['iris_plan']
        plan_resp = iris.client.get(iris.client.url + 'plans?name=%s&active=1' % iris_plan)
        if plan_resp.status_code != 200 or plan_resp.json() == []:
            raise HTTPBadRequest('invalid iris escalation plan', 'no iris plan named %s exists' % iris_plan)

    set_clause = ', '.join(['`{0}`=%s'.format(d) for d in data_cols if d in cols])
    query_params = tuple(data[d] for d in data_cols) + (team,)
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
    team = unquote(team)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()
    # Soft delete: set team inactive, delete future events for it
    cursor.execute('UPDATE `team` SET `active` = FALSE WHERE `name`=%s', team)
    cursor.execute('DELETE FROM `event` WHERE `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s) '
                   'AND `start` > UNIX_TIMESTAMP()', team)
    create_audit({}, team, TEAM_DELETED, req, cursor)
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()

    if deleted == 0:
        raise HTTPNotFound()
