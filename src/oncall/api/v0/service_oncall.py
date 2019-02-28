# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


def on_get(req, resp, service, role=None):
    '''
    Get the current user on-call for a given service/role. Returns event start/end, contact info,
    and user name.

    **Example request**

    .. sourcecode:: http

        GET /api/v0/services/service-foo/oncall/primary  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "contacts": {
                    "call": "+1 111-111-1111",
                    "email": "jdoe@example.com",
                    "im": "jdoe",
                    "sms": "+1 111-111-1111"
                },
                "end": 1495695600,
                "start": 1495263600,
                "user": "John Doe"
            }
        ]

    '''
    get_oncall_query = '''
        SELECT `user`.`full_name` AS `full_name`,
               `event`.`start`, `event`.`end`,
               `contact_mode`.`name` AS `mode`,
               `user_contact`.`destination`,
               `user`.`name` AS `user`,
               `team`.`name` AS `team`,
               `role`.`name` AS `role`
        FROM `event`
        JOIN `user` ON `event`.`user_id` = `user`.`id`
        JOIN `team` ON `event`.`team_id` = `team`.`id`
        JOIN `role` ON `role`.`id` = `event`.`role_id`
        LEFT JOIN `team_subscription` ON `subscription_id` = `team`.`id`
            AND `team_subscription`.`role_id` = `role`.`id`
        LEFT JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
        LEFT JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
        WHERE UNIX_TIMESTAMP() BETWEEN `event`.`start` AND `event`.`end`
            AND (`team`.`id` IN %s OR `team_subscription`.`team_id` IN %s)'''

    query_params = []
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    # Get subscription teams for teams owning the service, along with the teams that own the service
    cursor.execute('''SELECT `team_id`, `team`.`override_phone_number`, `team`.`name` FROM `team_service`
                      JOIN `service` ON `service`.`id` = `team_service`.`service_id`
                      JOIN `team` ON `team`.`id` = `team_service`.`team_id`
                      WHERE `service`.`name` = %s''',
                   service)
    data = cursor.fetchall()
    team_ids = [row['team_id'] for row in data]
    team_override_numbers = {row['name']: row['override_phone_number'] for row in data}
    if not team_ids:
        resp.body = json_dumps([])
        cursor.close()
        connection.close()
        return
    query_params += [team_ids, team_ids]
    if role is not None:
        get_oncall_query += ' AND `role`.`name` = %s'
        query_params.append(role)
    cursor.execute(get_oncall_query, query_params)
    data = cursor.fetchall()
    ret = {}
    for row in data:
        user = row['user']
        # add data row into accumulator only if not already there
        if user not in ret:
            ret[user] = row
            ret[user]['contacts'] = {}
        mode = row.pop('mode')
        if not mode:
            continue
        dest = row.pop('destination')
        ret[user]['contacts'][mode] = dest
    data = list(ret.values())
    for event in data:
        override_number = team_override_numbers.get(event['team'])
        if override_number and event['role'] == 'primary':
            event['contacts']['call'] = override_number
            event['contacts']['sms'] = override_number

    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
