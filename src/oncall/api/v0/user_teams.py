# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps
from ... import db
from falcon import HTTPNotFound


def on_get(req, resp, user_name):
    """
    Get active teams by user name. Note that this does not return any deleted teams that
    this user is a member of.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users/jdoe/teams  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "team-foo",
            "team-bar"
        ]
    """
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT `id` FROM `user` WHERE `name` = %s', user_name)
    if cursor.rowcount < 1:
        raise HTTPNotFound()
    user_id = cursor.fetchone()[0]
    cursor.execute('''SELECT `team`.`name` FROM `team`
                      JOIN `team_user` ON `team_user`.`team_id` = `team`.`id`
                      WHERE `team_user`.`user_id` = %s AND `team`.`active` = TRUE''', user_id)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = dumps(data)
