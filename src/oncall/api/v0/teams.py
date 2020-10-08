# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
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
    'active': '`team`.`active` = %s',
    'email': '`team`.`email` = %s',
    'email__eq': '`team`.`email` = %s',
    'email__contains': '`team`.`email` LIKE CONCAT("%%", %s, "%%")',
    'email__startswith': '`team`.`email` LIKE CONCAT(%s, "%%")',
    'email__endswith': '`team`.`email` LIKE CONCAT("%%", %s)',
}


def on_get(req, resp):
    '''
    Search for team names. Allows filtering based on a number of parameters, detailed below.
    Returns list of matching team names. If "active" parameter is unspecified, defaults to
    True (only displaying undeleted teams)

    :query name: team name
    :query name__eq: team name
    :query name__contains: team name contains param
    :query name__startswith: team name starts with param
    :query name__endswith: team name ends with param
    :query id: team id
    :query id__eq: team id
    :query active: team active/deleted (1 and 0, respectively)
    :query email: team email
    :query email__eq: team email
    :query email__contains: team email contains param
    :query email__startswith: team email starts with param
    :query email__endswith: team email ends with param

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/teams?name__startswith=team-  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "team-foo",
            "team-bar"
        ]

    '''

    query = 'SELECT `name`, `id` FROM `team`'
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
    data = [None]
    if req.get_param_as_bool('get_id'):
        data = [(r[0], r[1]) for r in cursor]
    else:
        data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp):
    '''
    Endpoint for team creation. The user who creates the team is automatically added as a
    team admin. Because of this, this endpoint cannot be called using an API key, otherwise
    a team would have no admins, making many team operations impossible.

    Teams can specify a number of attributes, detailed below:

    - name: the team's name. Teams must have unique names.
    - email: email address for the team.
    - slack_channel: slack channel for the team. Must start with '#'
    - slack_channel_notifications: slack channel for notifications. Must start with '#'
    - iris_plan: Iris escalation plan that incidents created from the Oncall UI will follow.

    If iris plan integration is not activated, this attribute can still be set, but its
    value is not used.

    Teams must specify ``name`` and ``scheduling_timezone``; other parameters are optional.

    **Example request:**

    .. sourcecode:: http

        POST api/v0/teams   HTTP/1.1
        Content-Type: application/json

        {
            "name": "team-foo",
            "scheduling_timezone": "US/Pacific",
            "email": "team-foo@example.com",
            "slack_channel": "#team-foo",
            "slack_channel_notifications": "#team-foo-alerts",
        }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

    :statuscode 201: Successful create
    :statuscode 400: Error in creating team. Possible errors: API key auth not allowed, invalid attributes, missing required attributes
    :statuscode 422: Duplicate team name
    '''
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
    slack_notifications = data.get('slack_channel_notifications')
    if slack_notifications and slack_notifications[0] != '#':
        raise HTTPBadRequest('invalid slack notifications channel',
                             'slack channel notifications name needs to start with #')
    email = data.get('email')
    iris_plan = data.get('iris_plan')
    iris_enabled = data.get('iris_enabled', False)
    override_number = data.get('override_phone_number')
    if not override_number:
        override_number = None

    # validate Iris plan if provided and Iris is configured
    if iris_plan is not None and iris.client is not None:
        plan_resp = iris.client.get(iris.client.url + 'plans?name=%s&active=1' % iris_plan)
        if plan_resp.status_code != 200 or plan_resp.json() == []:
            raise HTTPBadRequest('invalid iris escalation plan', 'no iris plan named %s exists' % iris_plan)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''INSERT INTO `team` (`name`, `slack_channel`, `slack_channel_notifications`, `email`, `scheduling_timezone`,
                                              `iris_plan`, `iris_enabled`, `override_phone_number`)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                       (team_name, slack, slack_notifications, email, scheduling_timezone, iris_plan, iris_enabled, override_number))

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
