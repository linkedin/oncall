# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from falcon import HTTP_201, HTTPError, HTTPBadRequest
from ujson import dumps as json_dumps
from ...auth import login_required, check_calendar_auth
from ... import db, constants
from ...utils import (
    load_json_body, user_in_team_by_name, create_notification, create_audit
)
from ...constants import EVENT_CREATED

columns = {
    'id': '`event`.`id` as `id`',
    'start': '`event`.`start` as `start`',
    'end': '`event`.`end` as `end`',
    'role': '`role`.`name` as `role`',
    'team': '`team`.`name` as `team`',
    'user': '`user`.`name` as `user`',
    'full_name': '`user`.`full_name` as `full_name`',
    'schedule_id': '`event`.`schedule_id`',
    'link_id': '`event`.`link_id`',
    'note': '`event`.`note`',
}

all_columns = ', '.join(columns.values())

constraints = {
    'id': '`event`.`id` = %s',
    'id__eq': '`event`.`id` = %s',
    'id__ne': '`event`.`id` != %s',
    'id__gt': '`event`.`id` > %s',
    'id__ge': '`event`.`id` >= %s',
    'id__lt': '`event`.`id` < %s',
    'id__le': '`event`.`id` <= %s',
    'start': '`event`.`start` = %s',
    'start__eq': '`event`.`start` = %s',
    'start__ne': '`event`.`start` != %s',
    'start__gt': '`event`.`start` > %s',
    'start__ge': '`event`.`start` >= %s',
    'start__lt': '`event`.`start` < %s',
    'start__le': '`event`.`start` <= %s',
    'end': '`event`.`end` = %s',
    'end__eq': '`event`.`end` = %s',
    'end__ne': '`event`.`end` != %s',
    'end__gt': '`event`.`end` > %s',
    'end__ge': '`event`.`end` >= %s',
    'end__lt': '`event`.`end` < %s',
    'end__le': '`event`.`end` <= %s',
    'role': '`role`.`name` = %s',
    'role__eq': '`role`.`name` = %s',
    'role__contains': '`role`.`name` LIKE CONCAT("%%", %s, "%%")',
    'role__startswith': '`role`.`name` LIKE CONCAT(%s, "%%")',
    'role__endswith': '`role`.`name` LIKE CONCAT("%%", %s)',
    'team': '`team`.`name` = %s',
    'team__eq': '`team`.`name` = %s',
    'team__contains': '`team`.`name` LIKE CONCAT("%%", %s, "%%")',
    'team__startswith': '`team`.`name` LIKE CONCAT(%s, "%%")',
    'team__endswith': '`team`.`name` LIKE CONCAT("%%", %s)',
    'team_id': '`team`.`id` = %s',
    'user': '`user`.`name` = %s',
    'user__eq': '`user`.`name` = %s',
    'user__contains': '`user`.`name` LIKE CONCAT("%%", %s, "%%")',
    'user__startswith': '`user`.`name` LIKE CONCAT(%s, "%%")',
    'user__endswith': '`user`.`name` LIKE CONCAT("%%", %s)'
}

TEAM_PARAMS = {'team', 'team__eq', 'team__contains', 'team__startswith', 'team_endswith', 'team_id'}


def on_get(req, resp):
    """
    Search for events. Allows filtering based on a number of parameters,
    detailed below.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/events?team=foo-sre&end__gt=1487466146&role=primary HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "start": 1488441600,
                "end": 1489132800,
                "team": "foo-sre",
                "link_id": null,
                "schedule_id": null,
                "role": "primary",
                "user": "foo",
                "full_name": "Foo Icecream",
                "id": 187795
            },
            {
                "start": 1488441600,
                "end": 1489132800,
                "team": "foo-sre",
                "link_id": "8a8ae77b8c52448db60c8a701e7bffc2",
                "schedule_id": 123,
                "role": "primary",
                "user": "bar",
                "full_name": "Bar Apple",
                "id": 187795
            }
        ]

    :query team: team name
    :query user: user name
    :query role: role name
    :query id: id of the event
    :query start: start time (unix timestamp) of event
    :query end: end time (unix timestamp) of event
    :query start__gt: start time (unix timestamp) greater than
    :query start__ge: start time (unix timestamp) greater than or equal
    :query start__lt: start time (unix timestamp) less than
    :query start__le: start time (unix timestamp) less than or equal
    :query end__gt: end time (unix timestamp) greater than
    :query end__ge: end time (unix timestamp) greater than or equal
    :query end__lt: end time (unix timestamp) less than
    :query end__le: end time (unix timestamp) less than or equal
    :query role__eq: role name
    :query role__contains: role name contains param
    :query role__startswith: role name starts with param
    :query role__endswith: role name ends with param
    :query team__eq: team name
    :query team__contains: team name contains param
    :query team__startswith: team name starts with param
    :query team__endswith: team name ends with param
    :query team_id: team id
    :query user__eq: user name
    :query user__contains: user name contains param
    :query user__startswith: user name starts with param
    :query user__endswith: user name ends with param

    :statuscode 200: no error
    :statuscode 400: bad request
    """
    fields = req.get_param_as_list('fields')
    if fields:
        fields = [columns[f] for f in fields if f in columns]
    req.params.pop('fields', None)
    include_sub = req.get_param_as_bool('include_subscribed')
    if include_sub is None:
        include_sub = True
    req.params.pop('include_subscribed', None)
    cols = ', '.join(fields) if fields else all_columns
    if any(key not in constraints for key in req.params):
        raise HTTPBadRequest('Bad constraint param')
    query = '''SELECT %s FROM `event`
               JOIN `user` ON `user`.`id` = `event`.`user_id`
               JOIN `team` ON `team`.`id` = `event`.`team_id`
               JOIN `role` ON `role`.`id` = `event`.`role_id`''' % cols

    where_params = []
    where_vals = []
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    # Build where clause. If including subscriptions, deal with team parameters later
    params = req.params.keys() - TEAM_PARAMS if include_sub else req.params
    for key in params:
        val = req.get_param(key)
        if key in constraints:
            where_params.append(constraints[key])
            where_vals.append(val)

    # Deal with team subscriptions and team parameters
    team_where = []
    subs_vals = []
    team_params = req.params.keys() & TEAM_PARAMS
    if include_sub and team_params:

        for key in team_params:
            val = req.get_param(key)
            team_where.append(constraints[key])
            subs_vals.append(val)
        subs_and = ' AND '.join(team_where)
        cursor.execute('''SELECT `subscription_id`, `role_id` FROM `team_subscription`
                          JOIN `team` ON `team_id` = `team`.`id`
                          WHERE %s''' % subs_and,
                       subs_vals)
        if cursor.rowcount != 0:
            # Build where clause based on team params and subscriptions
            subs_and = '(%s OR (%s))' % (subs_and, ' OR '.join(['`team`.`id` = %s AND `role`.`id` = %s' %
                                                                (row['subscription_id'], row['role_id']) for row in cursor]))
        where_params.append(subs_and)
        where_vals += subs_vals

    where_query = ' AND '.join(where_params)
    if where_query:
        query = '%s WHERE %s' % (query, where_query)
    cursor.execute(query, where_vals)
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp):
    """
    Endpoint for creating event. Responds with event id for created event. Events must
    specify the following parameters:

    - start: Unix timestamp for the event start time (seconds)
    - end: Unix timestamp for the event end time (seconds)
    - user: Username for the event's user
    - team: Name for the event's team
    - role: Name for the event's role

    All of these parameters are required.

    **Example request:**

    .. sourcecode:: http

        POST api/v0/events   HTTP/1.1
        Content-Type: application/json

        {
            "start": 1493667700,
            "end": 149368700,
            "user": "jdoe",
            "team": "team-foo",
            "role": "primary",
        }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

        1


    :statuscode 201: Event created
    :statuscode 400: Event validation checks failed
    :statuscode 422: Event creation failed: nonexistent role/event/team
    """
    data = load_json_body(req)
    now = time.time()
    if data['start'] < now - constants.GRACE_PERIOD:
        raise HTTPBadRequest('Invalid event', 'Creating events in the past not allowed')
    if data['start'] >= data['end']:
        raise HTTPBadRequest('Invalid event', 'Event must start before it ends')
    check_calendar_auth(data['team'], req)

    columns = ['`start`', '`end`', '`user_id`', '`team_id`', '`role_id`']
    values = ['%(start)s', '%(end)s',
              '(SELECT `id` FROM `user` WHERE `name`=%(user)s)',
              '(SELECT `id` FROM `team` WHERE `name`=%(team)s)',
              '(SELECT `id` FROM `role` WHERE `name`=%(role)s)']

    if 'schedule_id' in data:
        columns.append('`schedule_id`')
        values.append('%(schedule_id)s')

    if 'note' in data:
        columns.append('`note`')
        values.append('%(note)s')

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    if not user_in_team_by_name(cursor, data['user'], data['team']):
        raise HTTPBadRequest('Invalid event', 'User must be part of the team')

    try:
        query = 'INSERT INTO `event` (%s) VALUES (%s)' % (','.join(columns), ','.join(values))
        cursor.execute(query, data)
        event_id = cursor.lastrowid

        cursor.execute('SELECT team_id, role_id, user_id, start, full_name '
                       'FROM event JOIN user ON user.`id` = user_id WHERE event.id=%s', event_id)
        ev_info = cursor.fetchone()
        context = {
            'team': data['team'],
            'role': data['role'],
            'full_name': ev_info['full_name']
        }
        create_notification(context, ev_info['team_id'],
                            [ev_info['role_id']],
                            EVENT_CREATED,
                            [ev_info['user_id']],
                            cursor,
                            start_time=ev_info['start'])
        create_audit({'new_event_id': event_id, 'request_body': data},
                     data['team'],
                     EVENT_CREATED,
                     req,
                     cursor)
        connection.commit()
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'role_id\' cannot be null':
            err_msg = 'role "%s" not found' % data['role']
        elif err_msg == 'Column \'user_id\' cannot be null':
            err_msg = 'user "%s" not found' % data['user']
        elif err_msg == 'Column \'team_id\' cannot be null':
            err_msg = 'team "%s" not found' % data['team']
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps(event_id)
