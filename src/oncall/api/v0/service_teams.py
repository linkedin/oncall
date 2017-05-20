# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps
from ... import db


def on_get(req, resp, service):
    """
    Get list of team mapped to a service

    **Example request**

    .. sourcecode:: http

        GET /api/v0/services/service-foo/teams  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            "team-foo"
        ]
    """
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''SELECT `team`.`name` FROM `service`
                      JOIN `team_service` ON `team_service`.`service_id`=`service`.`id`
                      JOIN `team` ON `team`.`id`=`team_service`.`team_id`
                      WHERE `service`.`name`=%s''', service)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = dumps(data)
