# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound

from ...auth import login_required, check_team_auth
from ... import db
from ...utils import unsubscribe_notifications, create_audit
from ...constants import ADMIN_DELETED


@login_required
def on_delete(req, resp, team, user):
    """
    Delete team admin user. Removes admin from the team if he/she is not a member of any roster.

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/teams/team-foo/admins/jdoe HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: Team admin not found
    """
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''DELETE FROM `team_admin`
                      WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                      AND `user_id`=(SELECT `id` FROM `user` WHERE `name`=%s)''',
                   (team, user))
    deleted = cursor.rowcount
    if deleted == 0:
        raise HTTPNotFound()
    create_audit({'user': user}, team, ADMIN_DELETED, req, cursor)

    # Remove user from the team if needed
    query = '''DELETE FROM `team_user` WHERE `user_id` = (SELECT `id` FROM `user` WHERE `name`=%s) AND `user_id` NOT IN
                   (SELECT `roster_user`.`user_id`
                    FROM `roster_user` JOIN `roster` ON `roster`.`id` = `roster_user`.`roster_id`
                    WHERE team_id = (SELECT `id` FROM `team` WHERE `name`=%s)
                   UNION
                   (SELECT `user_id` FROM `team_admin`
                    WHERE `team_id` = (SELECT `id` FROM `team` WHERE `name`=%s)))
               AND `team_user`.`team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)'''
    cursor.execute(query, (user, team, team, team))
    if cursor.rowcount != 0:
        unsubscribe_notifications(team, user, cursor)
    connection.commit()
    cursor.close()
    connection.close()
