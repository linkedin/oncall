# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps as json_dumps


def on_get(req, resp):
    """
    Returns all notification types and whether they are reminder notifications.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/notification_types HTTP/1.1
        Host: example.com

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "name": "oncall_reminder",
                "is_reminder": 1
            }
        ]
    """
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('SELECT `name`, `is_reminder` FROM `notification_type`')
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
