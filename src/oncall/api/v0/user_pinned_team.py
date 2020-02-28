# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...auth import login_required, check_user_auth
from falcon import HTTPNotFound


@login_required
def on_delete(req, resp, user_name, team_name):
    '''
    Delete a pinned team

    **Example request:**

    .. sourcecode:: http

       DELETE /api/v0/users/jdoe/pinned_teams/team-foo HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 403: Delete not allowed; logged in user does not match user_name
    :statuscode 404: Team not found in user's pinned teams
    '''
    check_user_auth(user_name, req)
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''DELETE FROM `pinned_team`
                      WHERE `user_id` = (SELECT `id` FROM `user` WHERE `name` = %s)
                      AND `team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)''',
                   (user_name, team_name))
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()
    if deleted == 0:
        raise HTTPNotFound()
