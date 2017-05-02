# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from .events import all_columns
from ujson import dumps as json_dumps


def on_get(req, resp, user_name):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    role = req.get_param('role', None)
    limit = req.get_param_as_int('limit', None)
    query_end = ' ORDER BY `event`.`start` ASC'
    query = '''SELECT %s, (SELECT COUNT(*) FROM `event` `counter`
                           WHERE `counter`.`link_id` = `event`.`link_id`) AS num_events
               FROM `event`
               JOIN `user` ON `user`.`id` = `event`.`user_id`
               JOIN `team` ON `team`.`id` = `event`.`team_id`
               JOIN `role` ON `role`.`id` = `event`.`role_id`
               LEFT JOIN `event` `e2` ON `event`.link_id = `e2`.`link_id` AND `e2`.`start` < `event`.`start`
               WHERE `user`.`id` = (SELECT `id` FROM `user` WHERE `name` = %%s)
                   AND `event`.`start` > UNIX_TIMESTAMP()
                   AND `e2`.`start` IS NULL''' % all_columns

    query_params = [user_name]
    if role:
        query_end = ' AND `role`.`name` = %s' + query_end
        query_params.append(role)
    if limit:
        query_end += ' LIMIT %s'
        query_params.append(limit)
    cursor.execute(query + query_end, query_params)
    data = cursor.fetchall()
    resp.body = json_dumps(data)
