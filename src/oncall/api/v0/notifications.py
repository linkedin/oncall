# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db

columns = {
    'id': '`notification`.`id` = %s',
    'event_id': '`notification`.`event_id` = %s',
    'active': '`notification`.`active` = %s'
}


def on_get(req, resp):
    query = 'SELECT * FROM `notification`'
    where = []
    where_vals = []
    for col in req.params:
        if col in columns:
            where.append(columns[col])
            where_vals.append(req.get_param(col))
    if where:
        query += 'WHERE %s' % ', '.join(where)
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(query, where_vals)
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)