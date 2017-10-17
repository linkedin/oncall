from ... import db
from ujson import dumps as json_dumps
from falcon import HTTPNotFound, HTTPBadRequest


def on_get(req, resp, team, roster, role):
    start = req.get_param_as_int('start', required=True)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT id FROM role WHERE name = %s', role)
        if cursor.rowcount == 0:
            raise HTTPBadRequest('Invalid role')
        role_id = cursor.fetchone()[0]

        cursor.execute('SELECT id FROM team WHERE name = %s', team)
        if cursor.rowcount == 0:
            raise HTTPBadRequest('Invalid team')
        team_id = cursor.fetchone()[0]

        cursor.execute('SELECT id FROM roster WHERE name = %s and team_id = %s', (roster, team_id))
        if cursor.rowcount == 0:
            raise HTTPBadRequest('Invalid roster')
        roster_id = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM roster_user WHERE roster_id = %s', roster_id)
        if cursor.rowcount == 0:
            raise HTTPNotFound()
        roster_size = cursor.fetchone()[0]
        length = 604800 * roster_size

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
                       {'team_id': team_id,
                        'roster_id': roster_id,
                        'role_id': role_id,
                        'past': start - length,
                        'start': start,
                        'future': start + length})
        candidate = None
        max_score = -1
        # Find argmax(min(time between start and last event, time before start and next event))
        # If no next/last event exists, set value to infinity
        # This should maximize gaps between shifts
        for (user, before, after) in cursor:
            before = start - before if before is not None else float('inf')
            after = after - start if after is not None else float('inf')
            score = min(before, after)
            if score > max_score:
                candidate = user
                max_score = score
    finally:
        cursor.close()
        connection.close()
    resp.body = json_dumps({'user': candidate})
