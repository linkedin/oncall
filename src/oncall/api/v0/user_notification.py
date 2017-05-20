# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPBadRequest
from ... import db
from ...auth import login_required, check_user_auth
from ...utils import load_json_body

columns = {'team': '`team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)',
           'mode': '`mode_id` = (SELECT `id` FROM `contact_mode` WHERE `name` = %s)',
           'type': '`type_id` = (SELECT `id` FROM `notification_type` WHERE `name` = %s)',
           'time_before': '`time_before` = %s',
           'only_if_involved': '`only_if_involved` = %s'}


@login_required
def on_delete(req, resp, notification_id):
    '''
    Delete user notification settings by id.

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/notifications/1234  HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: Notification setting not found
    '''
    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT `user`.`name` FROM `notification_setting` '
                       'JOIN `user` ON `notification_setting`.`user_id` = `user`.`id` '
                       'WHERE `notification_setting`.`id` = %s', notification_id)
        username = cursor.fetchone()[0]
        check_user_auth(username, req)
        cursor.execute('DELETE FROM notification_setting WHERE `id` = %s', notification_id)
        num_deleted = cursor.rowcount
    except:
        raise
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()
    if num_deleted != 1:
        raise HTTPNotFound()


@login_required
def on_put(req, resp, notification_id):
    '''
    Edit user notification settings. Allows editing of the following attributes:

    - roles: list of role names
    - team: team name
    - mode: contact mode name
    - type: string defining what event to notify on. Types are detailed in notification
            POST documentation
    - time_before: in units of seconds (if reminder setting)
    - only_if_involved: boolean (if notification setting)

    **Example request**

        .. sourcecode:: http

            PUT /api/v0/events/1234 HTTP/1.1
            Content-Type: application/json

            {
                "team": "team-bar",
                "mode": "call",
                "user": "asmith",
                "roles": ["secondary"]
            }

    :statuscode 200: Successful edit
    :statuscode 400: Validation checks failed.
    '''
    data = load_json_body(req)
    params = data.keys()
    roles = data.pop('roles')

    cols = [columns[c] for c in data if c in columns]
    query_params = [data[c] for c in params if c in columns]
    query = 'UPDATE notification_setting SET %s WHERE id = %%s' % ', '.join(cols)
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    try:
        notification_type = data.get('type')
        cursor.execute('''SELECT `is_reminder`, `time_before`, `only_if_involved` FROM `notification_setting`
                          JOIN `notification_type` ON `notification_setting`.`type_id` = `notification_type`.`id`
                          WHERE `notification_setting`.`id` = %s''', notification_id)
        current_setting = cursor.fetchone()
        is_reminder = current_setting['is_reminder']
        if notification_type:
            cursor.execute('SELECT is_reminder FROM notification_type WHERE name = %s', notification_type)
            is_reminder = cursor.fetchone()['is_reminder']
        time_before = data.get('time_before', current_setting['time_before'])
        only_if_involved = data.get('only_if_involved', current_setting['only_if_involved'])

        if is_reminder and only_if_involved is not None:
            raise HTTPBadRequest('invalid setting update',
                                 'reminder setting must define only time_before')
        elif not is_reminder and time_before is not None:
            raise HTTPBadRequest('invalid setting update',
                                 'notification setting must define only only_if_involved')

        if cols:
            cursor.execute('SELECT `user`.`name` FROM `notification_setting` '
                           'JOIN `user` ON `notification_setting`.`user_id` = `user`.`id` '
                           'WHERE `notification_setting`.`id` = %s', notification_id)
            username = cursor.fetchone()['name']
            check_user_auth(username, req)
            cursor.execute(query, query_params + [notification_id])
        if roles:
            cursor.execute('DELETE FROM `setting_role` WHERE `setting_id` = %s', notification_id)
            query_vals = ', '.join(['(%s, (SELECT `id` FROM `role` WHERE `name` = %%s))'
                                    % notification_id] * len(roles))
            cursor.execute('INSERT INTO `setting_role`(`setting_id`, `role_id`) VALUES ' + query_vals,
                           roles)
    except:
        raise
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()
