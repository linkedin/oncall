# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTP_201, HTTPError, HTTPBadRequest, HTTPNotFound, HTTPForbidden
import time

from ujson import dumps as json_dumps
from ... import db
from ...utils import (
    load_json_body, gen_link_id, user_in_team_by_name, create_notification, create_audit
)
from ...auth import login_required, check_calendar_auth
from ...constants import EVENT_DELETED

@login_required
def on_delete(req, resp, link_id):
    """
    Delete a set of linked events using the link_id, anyone on the team can delete that team's events

    **Example request:**

    .. sourcecode:: http

       DELETE /api/v0/events/link/1234 HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 403: Delete not allowed; logged in user is not a team member
    :statuscode 404: Events not found
    """
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute('''SELECT `team`.`name` AS `team`, `event`.`team_id`, `role`.`name` AS `role`,
                             `event`.`role_id`, `event`.`start`, `user`.`full_name`, `event`.`user_id`
                      FROM `event`
                      JOIN `team` ON `event`.`team_id` = `team`.`id`
                      JOIN `role` ON `event`.`role_id` = `role`.`id`
                      JOIN `user` ON `event`.`user_id` = `user`.`id`
                      WHERE `event`.`link_id` = %s
                      ORDER BY `event`.`start`''', link_id)
    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        raise HTTPNotFound()
    data = cursor.fetchall()
    ev = data[0]

    try:
        check_calendar_auth(ev['team'], req)
    except HTTPForbidden:
        cursor.close()
        connection.close()
        raise

    cursor.execute('DELETE FROM `event` WHERE `link_id`=%s', link_id)

    context = {'team': ev['team'], 'full_name': ev['full_name'], 'role': ev['role']}
    create_notification(context, ev['team_id'], [ev['role_id']], EVENT_DELETED, [ev['user_id']], cursor,
                        start_time=ev['start'])
    create_audit({'old_event': data}, ev['team'], EVENT_DELETED, req, cursor)

    connection.commit()
    cursor.close()
    connection.close()