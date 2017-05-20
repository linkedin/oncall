# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


def on_get(req, resp, service, role):
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
    get_oncall_query = '''SELECT `user`.`full_name` AS `user`, `event`.`start`, `event`.`end`,
                              `contact_mode`.`name` AS `mode`, `user_contact`.`destination`
                          FROM `service` JOIN `team_service` ON `service`.`id` = `team_service`.`service_id`
                              JOIN `event` ON `event`.`team_id` = `team_service`.`team_id`
                              JOIN `user` ON `user`.`id` = `event`.`user_id`
                              JOIN `role` ON `role`.`id` = `event`.`role_id` AND `role`.`name` = %s
                              LEFT JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
                              LEFT JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
                          WHERE UNIX_TIMESTAMP() BETWEEN `event`.`start` AND `event`.`end`
                              AND `service`.`name` = %s'''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(get_oncall_query, (role, service))
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
    data = ret.values()

    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
