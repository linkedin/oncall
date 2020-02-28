# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps as json_dumps
from falcon import HTTPNotFound, HTTPBadRequest


def on_get(req, resp, team, roster, role):
    start = req.get_param_as_int('start', required=True)
    end = req.get_param_as_int('end', required=True)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT id FROM role WHERE name = %s', role)
        if cursor.rowcount == 0:
            raise HTTPBadRequest('Invalid role')
        role_id = cursor.fetchone()[0]

        cursor.execute('''SELECT `team`.`id`, `roster`.`id` FROM `team` JOIN `roster` ON `roster`.`team_id` = `team`.`id`
                          WHERE `roster`.`name` = %s and `team`.`name` = %s''', (roster, team))
        if cursor.rowcount == 0:
            raise HTTPBadRequest('Invalid roster')
        team_id, roster_id = cursor.fetchone()

        cursor.execute('SELECT COUNT(*) FROM roster_user WHERE roster_id = %s', roster_id)
        if cursor.rowcount == 0:
            raise HTTPNotFound()
        roster_size = cursor.fetchone()[0]
        length = 604800 * roster_size

        data = {'team_id': team_id,
                'roster_id': roster_id,
                'role_id': role_id,
                'past': start - length,
                'start': start,
                'end': end,
                'future': start + length}

        cursor.execute('''SELECT `user`.`name` FROM `event` JOIN `user` ON `event`.`user_id` = `user`.`id`
                          WHERE `team_id` = %(team_id)s AND %(start)s < `event`.`end` AND %(end)s > `event`.`start`''',
                       data)
        busy_users = set(row[0] for row in cursor)

        cursor.execute('''SELECT * FROM
                            (SELECT `user`.`name` AS `user`, MAX(`event`.`start`) AS `before`
                             FROM `roster_user` JOIN `user` ON `user`.`id` = `roster_user`.`user_id`
                               AND roster_id = %(roster_id)s AND `roster_user`.`in_rotation` = 1
                             LEFT JOIN `event` ON `event`.`user_id` = `user`.`id` AND `team_id` = %(team_id)s
                               AND `role_id` = %(role_id)s AND `start` BETWEEN %(past)s AND %(start)s
                             GROUP BY `user`.`name`) past
                          JOIN
                            (SELECT `user`.`name` AS `user`, MIN(`event`.`start`) AS `after`
                             FROM `roster_user` JOIN `user` ON `user`.`id` = `roster_user`.`user_id`
                               AND roster_id = %(roster_id)s AND `roster_user`.`in_rotation` = 1
                             LEFT JOIN `event` ON `event`.`user_id` = `user`.`id` AND `team_id` = %(team_id)s
                               AND `role_id` = %(role_id)s AND `start` BETWEEN %(start)s AND %(future)s
                             GROUP BY `user`.`name`) future
                          USING (`user`)''',
                       data)
        candidate = None
        max_score = -1
        # Find argmax(min(time between start and last event, time before start and next event))
        # If no next/last event exists, set value to infinity
        # This should maximize gaps between shifts
        ret = {}
        for (user, before, after) in cursor:
            if user in busy_users:
                continue
            before = start - before if before is not None else float('inf')
            after = after - start if after is not None else float('inf')
            score = min(before, after)
            ret[user] = score if score != float('inf') else 'infinity'
            if score > max_score:
                candidate = user
                max_score = score
    finally:
        cursor.close()
        connection.close()
    resp.body = json_dumps({'user': candidate, 'data': ret})
