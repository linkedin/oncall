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
    resp.body = json_dumps(data.values())


@login_required
def on_post(req, resp, user_name):
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
