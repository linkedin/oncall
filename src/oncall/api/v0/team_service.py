# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote

from falcon import HTTPNotFound

from ...auth import login_required, check_team_auth
from ... import db


@login_required
def on_delete(req, resp, team, service):
    """
    Delete service team mapping
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
