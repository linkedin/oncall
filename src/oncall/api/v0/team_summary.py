# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps
from collections import defaultdict
from falcon import HTTPNotFound


def on_get(req, resp, team):
    '''
    Endpoint to get a summary of the team's oncall information. Returns an object
    containing the fields ``current`` and ``next``, which then contain information
    on the current and next on-call shifts for this team. ``current`` and ``next``
    are objects keyed by role (if an event of that role exists), with values of
    lists of event/user information. This list will have multiple elements if
    multiple events with the same role are currently occurring, or if multiple
    events with the same role are starting next in the future at the same time.

    If no event with a given role exists, that role is excluded from the ``current``
    or ``next`` object. If no events exist, the ``current`` and ``next`` objects
    will be empty objects.

    **Example request:**

    .. sourcecode:: http

        GET api/v0/teams/team-foo/summary   HTTP/1.1
        Content-Type: application/json

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "current": {
                "manager": [
                    {
                        "end": 1495760400,
                        "full_name": "John Doe",
                        "photo_url": "example.image.com",
                        "role": "manager",
                        "start": 1495436400,
                        "user": "jdoe",
                        "user_contacts": {
                            "call": "+1 111-111-1111",
                            "email": "jdoe@example.com",
                            "im": "jdoe",
                            "sms": "+1 111-111-1111"
                        },
                        "user_id": 1234
                    }
                ],
                "primary": [
                    {
                        "end": 1495760400,
                        "full_name": "Adam Smith",
                        "photo_url": "example.image.com",
                        "role": "primary",
                        "start": 1495350000,
                        "user": "asmith",
                        "user_contacts": {
                            "call": "+1 222-222-2222",
                            "email": "asmith@example.com",
                            "im": "asmith",
                            "sms": "+1 222-222-2222"
                        },
                        "user_id": 1235
                    }
                ]
            },
            "next": {
                "manager": [
                    {
                        "end": 1496127600,
                        "full_name": "John Doe",
                        "photo_url": "example.image.com",
                        "role": "manager",
                        "start": 1495436400,
                        "user": "jdoe",
                        "user_contacts": {
                            "call": "+1 111-111-1111",
                            "email": "jdoe@example.com",
                            "im": "jdoe",
                            "sms": "+1 111-111-1111"
                        },
                        "user_id": 1234
                    }
                ],
                "primary": [
                    {
                        "end": 1495760400,
                        "full_name": "Adam Smith",
                        "photo_url": "example.image.com",
                        "role": "primary",
                        "start": 1495350000,
                        "user": "asmith",
                        "user_contacts": {
                            "call": "+1 222-222-2222",
                            "email": "asmith@example.com",
                            "im": "asmith",
                            "sms": "+1 222-222-2222"
                        },
                        "user_id": 1235
                    }
                ]
            }
        }

    '''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute('SELECT `id`, `override_phone_number` FROM `team` WHERE `name` = %s', team)
    if cursor.rowcount < 1:
        raise HTTPNotFound()
    data = cursor.fetchone()
    team_id = data['id']
    override_num = data['override_phone_number']
    current_query = '''
        SELECT `user`.`full_name` AS `full_name`,
               `user`.`photo_url`,
               `event`.`start`, `event`.`end`,
               `event`.`user_id`,
               `user`.`name` AS `user`,
               `team`.`name` AS `team`,
               `role`.`name` AS `role`
        FROM `event`
        JOIN `user` ON `event`.`user_id` = `user`.`id`
        JOIN `team` ON `event`.`team_id` = `team`.`id`
        JOIN `role` ON `role`.`id` = `event`.`role_id`
        WHERE UNIX_TIMESTAMP() BETWEEN `event`.`start` AND `event`.`end`'''
    team_where = '`team`.`id` = %s'
    cursor.execute('''SELECT `subscription_id`, `role_id` FROM `team_subscription`
                      JOIN `team` ON `team_id` = `team`.`id`
                      WHERE %s''' % team_where,
                   team_id)

    if cursor.rowcount != 0:
        # Check conditions are true for either team OR subscriber
        team_where = '(%s OR (%s))' % (team_where, ' OR '.join(
            ['`event`.`team_id` = %s AND `event`.`role_id` = %s' %
             (row['subscription_id'], row['role_id']) for row in cursor]))

    cursor.execute(' AND '.join((current_query, team_where)), team_id)
    payload = {}
    users = set([])
    payload['current'] = defaultdict(list)
    for event in cursor:
        payload['current'][event['role']].append(event)
        users.add(event['user_id'])

    next_query = '''
        SELECT `role`.`name` AS `role`,
               `user`.`full_name` AS `full_name`,
               `event`.`start`,
               `event`.`end`,
               `user`.`photo_url`,
               `user`.`name` AS `user`,
               `event`.`user_id`,
               `event`.`role_id`,
               `event`.`team_id`
        FROM `event`
        JOIN `role` ON `event`.`role_id` = `role`.`id`
        JOIN `user` ON `event`.`user_id` = `user`.`id`

        JOIN (SELECT `event`.`role_id`, `event`.`team_id`, MIN(`event`.`start` - UNIX_TIMESTAMP()) AS dist
              FROM `event` JOIN `team` ON `team`.`id` = `event`.`team_id`
              WHERE `start` > UNIX_TIMESTAMP() AND %s
              GROUP BY `event`.`role_id`, `event`.`team_id`) AS t1
            ON `event`.`role_id` = `t1`.`role_id`
                AND `event`.`start` - UNIX_TIMESTAMP() = `t1`.dist
                AND `event`.`team_id` = `t1`.`team_id`''' % team_where
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
    if override_num:
        try:
            for event in payload['current']['primary']:
                event['user_contacts']['call'] = override_num
                event['user_contacts']['sms'] = override_num
        except KeyError:
            # No current primary events exist, do nothing
            pass

    resp.body = dumps(payload)
