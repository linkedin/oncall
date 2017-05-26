# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


get_oncall_query = '''
    SELECT `user`.`full_name` AS `full_name`,
            `event`.`start`, `event`.`end`,
            `contact_mode`.`name` AS `mode`,
            `user_contact`.`destination`,
            `user`.`name` as `user`
    FROM `event`
    JOIN `user` ON `event`.`user_id` = `user`.`id`
    JOIN `team` ON `event`.`team_id` = `team`.`id`
    JOIN `role` ON `role`.`id` = `event`.`role_id` AND `role`.`name` = %s
    LEFT JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
    LEFT JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
    WHERE UNIX_TIMESTAMP() BETWEEN `event`.`start` AND `event`.`end`
        AND `team`.`name` = %s'''


def on_get(req, resp, team, role):
    """
    Get current active event for team based on given role.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/teams/team_ops/oncall/primary HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       [
         {
           "user": "foo",
           "start": 1487426400,
           "end": 1487469600,
           "full_name": "Foo Icecream",
           "contacts": {
             "im": "foo",
             "sms": "+1 123-456-7890",
             "email": "foo@example.com",
             "call": "+1 123-456-7890"
           }
         },
         {
           "user": "bar",
           "start": 1487426400,
           "end": 1487469600,
           "full_name": "Bar Dog",
           "contacts": {
             "im": "bar",
             "sms": "+1 123-456-7890",
             "email": "bar@example.com",
             "call": "+1 123-456-7890"
           }
         }
       ]

    :statuscode 200: no error
    """
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(get_oncall_query, (role, team))
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
