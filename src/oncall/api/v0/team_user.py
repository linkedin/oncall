# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote

from falcon import HTTPNotFound

from ...auth import login_required, check_team_auth
from ... import db


@login_required
def on_delete(req, resp, team, user):
    """
    Delete user from a team

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/teams/team-foo/users/jdoe HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: User not found in team
    """
    team = unquote(team)
    check_team_auth(team, req)
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''DELETE FROM `team_user`
                      WHERE `team_id`=(SELECT `id` FROM `team` WHERE `name`=%s)
                      AND `user_id`=(SELECT `id` FROM `user` WHERE `name`=%s)''',
                   (team, user))
    deleted = cursor.rowcount
    if deleted == 0:
        raise HTTPNotFound()

    connection.commit()
    cursor.close()
    connection.close()
