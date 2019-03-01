# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


def on_get(req, resp, team, role=None):
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
        LEFT JOIN `team` `subscriber` ON `subscriber`.`id` = `team_subscription`.`team_id`
        LEFT JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
        LEFT JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
        WHERE UNIX_TIMESTAMP() BETWEEN `event`.`start` AND `event`.`end`
            AND (`team`.`name` = %s OR `subscriber`.`name` = %s)'''
    query_params = [team, team]
    if role is not None:
        get_oncall_query += ' AND `role`.`name` = %s'
        query_params.append(role)

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(get_oncall_query, query_params)
    data = cursor.fetchall()
    cursor.execute('SELECT `override_phone_number` FROM team WHERE `name` = %s', team)
    team = cursor.fetchone()
    override_number = team['override_phone_number'] if team else None
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
        if override_number and event['role'] == 'primary':
            event['contacts']['call'] = override_number
            event['contacts']['sms'] = override_number

    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
