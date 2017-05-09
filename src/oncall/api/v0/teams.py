# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote
from falcon import HTTPError, HTTP_201, HTTPBadRequest
from ujson import dumps as json_dumps
from ...utils import load_json_body, invalid_char_reg, subscribe_notifications, create_audit
from ...constants import TEAM_CREATED

from ... import db, iris
from ...auth import login_required

constraints = {
    'name': '`team`.`name` = %s',
    'name__eq': '`team`.`name` = %s',
    'name__contains': '`team`.`name` LIKE CONCAT("%%", %s, "%%")',
    'name__startswith': '`team`.`name` LIKE CONCAT(%s, "%%")',
    'name__endswith': '`team`.`name` LIKE CONCAT("%%", %s)',
    'id': '`team`.`id` = %s',
    'id__eq': '`team`.`id` = %s',
    'active': '`team`.`active` = %s'
}


def on_get(req, resp):

    query = 'SELECT `name`, `email`, `slack_channel`, `scheduling_timezone`, `iris_plan` FROM `team`'
    if 'active' not in req.params:
        req.params['active'] = True

    connection = db.connect()
    cursor = connection.cursor()
    keys = []
    query_values = []
    for key in req.params:
        value = req.get_param(key)
        if key in constraints:
            keys.append(key)
            query_values.append(value)
    where_query = ' AND '.join(constraints[key]for key in keys)
    if where_query:
        query = '%s WHERE %s' % (query, where_query)

    cursor.execute(query, query_values)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp):
    if 'user' not in req.context:
        # ban API auth because we don't know who to set as team admin
        raise HTTPBadRequest('invalid login', 'API key auth is not allowed for team creation')

    data = load_json_body(req)
    if not data.get('name'):
        raise HTTPBadRequest('', 'name attribute missing from request')
    if not data.get('scheduling_timezone'):
        raise HTTPBadRequest('', 'scheduling_timezone attribute missing from request')
    team_name = unquote(data['name'])
    invalid_char = invalid_char_reg.search(team_name)
    if invalid_char:
        raise HTTPBadRequest('invalid team name',
                             'team name contains invalid character "%s"' % invalid_char.group())

    scheduling_timezone = unquote(data['scheduling_timezone'])
    slack = data.get('slack_channel')
    if slack and slack[0] != '#':
        raise HTTPBadRequest('invalid slack channel',
                             'slack channel name needs to start with #')
    email = data.get('email')
    iris_plan = data.get('iris_plan')

    # validate Iris plan if provided and Iris is configured
    if iris_plan is not None and iris.client is not None:
        plan_resp = iris.client.get(iris.client.url + 'plans?name=%s&active=1' % iris_plan)
        if plan_resp.status_code != 200 or plan_resp.json() == []:
            raise HTTPBadRequest('invalid iris escalation plan', 'no iris plan named %s exists' % iris_plan)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''
            INSERT INTO `team` (`name`, `slack_channel`, `email`, `scheduling_timezone`, `iris_plan`)
            VALUES (%s, %s, %s, %s, %s)''', (team_name, slack, email, scheduling_timezone, iris_plan))

        team_id = cursor.lastrowid
        query = '''
            INSERT INTO `team_user` (`team_id`, `user_id`)
            VALUES (%s, (SELECT `id` FROM `user` WHERE `name` = %s))'''
        cursor.execute(query, (team_id, req.context['user']))
        query = '''
            INSERT INTO `team_admin` (`team_id`, `user_id`)
            VALUES (%s, (SELECT `id` FROM `user` WHERE `name` = %s))'''
        cursor.execute(query, (team_id, req.context['user']))
        subscribe_notifications(team_name, req.context['user'], cursor)
        create_audit({'team_id': team_id}, data['name'], TEAM_CREATED, req, cursor)
        connection.commit()
    except db.IntegrityError:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'team name "%s" already exists' % team_name)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
