# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...auth import login_required, check_team_auth
from falcon import HTTPNotFound


@login_required
def on_delete(req, resp, team, subscription, role):
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''DELETE FROM `team_subscription`
                      WHERE team_id = (SELECT `id` FROM `team` WHERE `name` = %s)
                      AND `subscription_id` = (SELECT `id` FROM `team` WHERE `name` = %s)\
                      AND `role_id` = (SELECT `id` FROM `role` WHERE `name` = %s)''',
                   (team, subscription, role))
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()
    if deleted == 0:
        raise HTTPNotFound()
