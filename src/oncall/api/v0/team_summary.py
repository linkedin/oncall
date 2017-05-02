# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps
from collections import defaultdict
from falcon import HTTPNotFound


def on_get(req, resp, team):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute('SELECT `id` FROM `team` WHERE `name` = %s', team)
    if cursor.rowcount < 1:
        raise HTTPNotFound()
    team_id = cursor.fetchone()['id']

    current_query = '''
        SELECT `role`.`name` AS `role`, `user`.`full_name` AS `full_name`,
               `event`.`start`, `event`.`end`, `user`.`photo_url`, `event`.`user_id`
        FROM `event`
            JOIN `role` ON `event`.`role_id` = `role`.`id`
            JOIN `user` ON `event`.`user_id` = `user`.`id`
        WHERE `event`.`team_id` = %s
            AND UNIX_TIMESTAMP() >= `event`.`start`
            AND UNIX_TIMESTAMP() < `event`.`end`'''
    cursor.execute(current_query, team_id)
    payload = {}
    users = set([])
    payload['current'] = defaultdict(list)
    for event in cursor:
        payload['current'][event['role']].append(event)
        users.add(event['user_id'])

    next_query = '''
        SELECT `role`.`name` AS `role`, `user`.`full_name` AS `full_name`,
               `event`.`start`, `event`.`end`, `user`.`photo_url`, `event`.`user_id`
        FROM `event`
            JOIN `role` ON `event`.`role_id` = `role`.`id`
            JOIN `user` ON `event`.`user_id` = `user`.`id`
            JOIN (SELECT `role_id`, `team_id`, MIN(`start` - UNIX_TIMESTAMP()) AS dist
                  FROM `event`
                  WHERE `start` > UNIX_TIMESTAMP() AND `event`.`team_id` = %s
                  GROUP BY role_id) AS t1
                ON `event`.`role_id` = `t1`.`role_id`
                    AND `event`.`start` - UNIX_TIMESTAMP() = `t1`.dist
                    AND `event`.`team_id` = `t1`.`team_id`'''
    cursor.execute(next_query, team_id)
    payload['next'] = defaultdict(list)
    for event in cursor:
        payload['next'][event['role']].append(event)
        users.add(event['user_id'])

    if users:
        # TODO: write a test for empty users
        contacts_query = '''
            SELECT `contact_mode`.`name` AS `mode`,
                   `user_contact`.`destination`,
                   `user_contact`.`user_id`
            FROM `user`
                JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
                JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
            WHERE `user`.`id` IN %s'''

        cursor.execute(contacts_query, (users,))
        contacts = cursor.fetchall()

        for part in payload.values():
            for event_list in part.values():
                for event in event_list:
                    event['user_contacts'] = dict((c['mode'], c['destination'])
                                                  for c in contacts
                                                  if c['user_id'] == event['user_id'])

    cursor.close()
    connection.close()

    resp.body = dumps(payload)
