# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote

from falcon import HTTPNotFound
from ujson import dumps as json_dumps

from ...auth import login_required, check_team_auth
from ... import db


def on_get(req, resp):
    """
    Get list of team to service mappings

    **Example request**:

    .. sourcecode:: http

        GET /api/v0/team_services  HTTP/1.1
        Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "team": "team1",
                "service" : "service-foo"
            }
        ]
    """
    query = '''SELECT `team`.`name` as team_name, `service`.`name` as service_name FROM `team_service`
                      JOIN `service` ON `team_service`.`service_id`=`service`.`id`
                      JOIN `team` ON `team_service`.`team_id`=`team`.`id`'''
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute(query)
    data = [{'team': r[0], 'service': r[1]} for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_delete(req, resp, team, service):
    """
    Delete service team mapping. Only allowed for team admins.

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/teams/team-foo/services/service-foo HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: Team-service mapping not found
    """
    team = unquote(team)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''DELETE FROM `team_service`
                      WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                      AND `service_id`=(SELECT `id` FROM `service` WHERE `name`=%s)''',
                   (team, service))
    deleted = cursor.rowcount
    if deleted == 0:
        raise HTTPNotFound()

    connection.commit()
    cursor.close()
    connection.close()
