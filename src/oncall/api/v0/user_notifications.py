# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPBadRequest, HTTP_201
from ujson import dumps as json_dumps
from ... import db
from ...auth import login_required, check_user_auth
from ...utils import load_json_body

required_params = {'team', 'roles', 'mode', 'type'}
other_params = {'time_before', 'only_if_involved'}
all_params = required_params | other_params


def on_get(req, resp, user_name):
    '''
    Get all notification settings for a user by name.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users/jdoe/notifications  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "id": 21830,
                "mode": "email",
                "only_if_involved": null,
                "roles": [
                    "primary",
                    "secondary",
                    "shadow",
                    "manager"
                ],
                "team": "team-foo",
                "time_before": 86400,
                "type": "oncall_reminder"
            },
            {
                "id": 21831,
                "mode": "email",
                "only_if_involved": null,
                "roles": [
                    "primary",
                    "secondary",
                    "shadow",
                    "manager"
                ],
                "team": "team-foo",
                "time_before": 604800,
                "type": "oncall_reminder"
            }
        ]

    '''
    query = '''SELECT `team`.`name` AS `team`, `role`.`name` AS `role`, `contact_mode`.`name` AS `mode`,
                      `notification_type`.`name` AS `type`, `notification_setting`.`time_before`,
                      `notification_setting`.`only_if_involved`, `notification_setting`.`id`
               FROM `notification_setting` JOIN `user` ON `notification_setting`.`user_id` = `user`.`id`
                   JOIN `team` ON `notification_setting`.`team_id` = `team`.`id`
                   JOIN `contact_mode` ON `notification_setting`.`mode_id` = `contact_mode`.`id`
                   JOIN `notification_type` ON `notification_setting`.`type_id` = `notification_type`.`id`
                   JOIN `setting_role` ON `notification_setting`.`id` = `setting_role`.`setting_id`
                   JOIN `role` ON `setting_role`.`role_id` = `role`.`id`
               WHERE `user`.`name` = %s'''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(query, user_name)
    data = {}
    # Format roles
    for row in cursor:
        setting_id = row['id']
        if setting_id not in data:
            role = row.pop('role')
            row['roles'] = [role]
            data[setting_id] = row
        else:
            data[setting_id]['roles'].append(row['role'])

    cursor.close()
    connection.close()
    resp.body = json_dumps(list(data.values()))


@login_required
def on_post(req, resp, user_name):
    '''
    Endpoint to create notification settings for a user. Responds with an object denoting the created
    setting's id. Requests to create notification settings must define the following:

    - team
    - roles
    - mode
    - type

    Users will be notified via ``$mode`` if a ``$type`` action occurs on the ``$team`` calendar that
    modifies events having a role contained in ``$roles``. In addition to these parameters,
    notification settings must define one of ``time_before`` and ``only_if_involved``, depending
    on whether the notification type is a reminder or a notification. Reminders define a ``time_before``
    and reference the start/end time of an event that user is involved in. There are two reminder
    types: "oncall_reminder" and "offcall_reminder", referencing the start and end of on-call events,
    respectively. ``time_before`` is specified in seconds and denotes how far in advance the user
    should be reminded of an event.

    Notifications are event-driven, and created when a team's calendar is modified. By default,
    the notification types are:

    - event_created
    - event_edited
    - event_deleted
    - event_swapped
    - event_substituted

    Non-reminder settings must define ``only_if_involved`` which determines whether the user will
    be notified on all actions of the given typ or only on ones in which they are involved. Note
    that ``time_before`` must not be specified for a non-reminder setting, and ``only_if_involved``
    must not be specified for reminder settings.

    An authoritative list of notification types can be obtained from the /api/v0/notification_types
    GET endpoint, which also details whether the type is a reminder. This will obtain all
    notification type data from the database, and is an absolute source of truth for Oncall.

    **Example request:**

    .. sourcecode:: http

        POST api/v0/events   HTTP/1.1
        Content-Type: application/json

            {
                "team": "team-foo",
                "roles": ["primary", "secondary"],
                "mode": "email",
                "type": "event_created",
                "only_if_involved": true
            }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

            {
                "id": 1234
            }

    '''
    check_user_auth(user_name, req)
    data = load_json_body(req)

    params = set(data.keys())
    missing_params = required_params - params
    if missing_params:
        raise HTTPBadRequest('invalid notification setting',
                             'missing required parameters: %s' % ', '.join(missing_params))
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT is_reminder FROM notification_type WHERE name = %s', data['type'])

    # Validation checks: notification type must exist
    #                    only one of time_before and only_if_involved can be defined
    #                    reminder notifications must define time_before
    #                    other notifications must define only_if_involved
    if cursor.rowcount != 1:
        raise HTTPBadRequest('invalid notification setting',
                             'notification type %s does not exist' % data['type'])
    is_reminder = cursor.fetchone()[0]
    extra_cols = params & other_params
    if len(extra_cols) != 1:
        raise HTTPBadRequest('invalid notification setting',
                             'settings must define exactly one of %s' % other_params)
    extra_col = next(iter(extra_cols))
    if is_reminder and extra_col != 'time_before':
        raise HTTPBadRequest('invalid notification setting',
                             'reminder setting must define time_before')
    elif not is_reminder and extra_col != 'only_if_involved':
        raise HTTPBadRequest('invalid notification setting',
                             'notification setting must define only_if_involved')

    roles = data.pop('roles')
    data['user'] = user_name

    query = '''INSERT INTO `notification_setting` (`user_id`, `team_id`, `mode_id`, `type_id`, {0})
               VALUES ((SELECT `id` FROM `user` WHERE `name`= %(user)s),
                       (SELECT `id` FROM `team` WHERE `name` = %(team)s),
                       (SELECT `id` FROM `contact_mode` WHERE `name` = %(mode)s),
                       (SELECT `id` FROM `notification_type` WHERE `name` = %(type)s),
                       %({0})s)'''.format(extra_col)

    cursor.execute(query, data)
    if cursor.rowcount != 1:
        raise HTTPBadRequest('invalid request', 'unable to create notification with provided settings')
    setting_id = cursor.lastrowid

    query_vals = ', '.join(['(%d, (SELECT `id` FROM `role` WHERE `name` = %%s))' % setting_id] * len(roles))

    try:
        cursor.execute('INSERT INTO `setting_role`(`setting_id`, `role_id`) VALUES ' + query_vals, roles)
    except db.IntegrityError:
        raise HTTPBadRequest('invalid request', 'unable to create notification: invalid roles')
    connection.commit()
    cursor.close()
    connection.close()
    resp.body = json_dumps({'id': setting_id})
    resp.status = HTTP_201
