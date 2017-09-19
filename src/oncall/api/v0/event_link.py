# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from operator import itemgetter
from falcon import HTTPNotFound, HTTPBadRequest, HTTP_204
from ... import db, constants
from ...utils import (
    create_notification, create_audit, load_json_body, user_in_team_by_name
)
from ...auth import login_required, check_calendar_auth
from ...constants import EVENT_DELETED, EVENT_EDITED

update_columns = {
    'role': '`role_id`=(SELECT `id` FROM `role` WHERE `name`=%(role)s)',
    'user': '`user_id`=(SELECT `id` FROM `user` WHERE `name`=%(user)s)',
    'note': '`note`=%(note)s'
}


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

    try:
        cursor.execute('''SELECT `team`.`name` AS `team`, `event`.`team_id`, `role`.`name` AS `role`,
                             `event`.`role_id`, `event`.`start`, `user`.`full_name`, `event`.`user_id`
                      FROM `event`
                      JOIN `team` ON `event`.`team_id` = `team`.`id`
                      JOIN `role` ON `event`.`role_id` = `role`.`id`
                      JOIN `user` ON `event`.`user_id` = `user`.`id`
                      WHERE `event`.`link_id` = %s
                      ORDER BY `event`.`start`''', link_id)
        if cursor.rowcount == 0:
            raise HTTPNotFound()
        data = cursor.fetchall()
        ev = data[0]
        event_start = min(data, key=itemgetter('start'))['start']
        check_calendar_auth(ev['team'], req)
        if event_start < time.time() - constants.GRACE_PERIOD:
            raise HTTPBadRequest('Invalid event update',
                                 'Deleting events in the past not allowed')
        cursor.execute('DELETE FROM `event` WHERE `link_id`=%s', link_id)

        context = {'team': ev['team'], 'full_name': ev['full_name'], 'role': ev['role']}
        create_notification(context, ev['team_id'], [ev['role_id']], EVENT_DELETED, [ev['user_id']], cursor,
                            start_time=ev['start'])
        create_audit({'old_event': data}, ev['team'], EVENT_DELETED, req, cursor)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


@login_required
def on_put(req, resp, link_id):
    """
    Update an event by link_id; anyone can update any event within the team.
    Only username can be updated using this endpoint.

    **Example request:**

    .. sourcecode:: http

        PUT /api/v0/events/link/1234 HTTP/1.1
        Content-Type: application/json

        {
            "user": "asmith",
        }

    :statuscode 200: Successful update

    """
    data = load_json_body(req)
    try:
        update_cols = ', '.join(update_columns[col] for col in data)
    except KeyError:
        raise HTTPBadRequest('Invalid event update', 'Invalid column')
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    try:
        cursor.execute('''SELECT
                        `event`.`start`,
                        `event`.`end`,
                        `event`.`user_id`,
                        `event`.`role_id`,
                        `event`.`id`,
                        `team`.`name` AS `team`,
                        `role`.`name` AS `role`,
                        `user`.`name` AS `user`,
                        `user`.`full_name`,
                        `event`.`team_id`
                    FROM `event`
                    JOIN `team` ON `event`.`team_id` = `team`.`id`
                    JOIN `role` ON `event`.`role_id` = `role`.`id`
                    JOIN `user` ON `event`.`user_id` = `user`.`id`
                    WHERE `event`.`link_id`=%s''', link_id)
        event_data = cursor.fetchall()
        if len(event_data) == 0:
            raise HTTPNotFound()
        event_summary = event_data[0].copy()
        event_summary['end'] = max(event_data, key=itemgetter('end'))['end']
        event_summary['start'] = min(event_data, key=itemgetter('start'))['start']
        user = data.get('user', event_summary['user'])
        if not user_in_team_by_name(cursor, user, event_summary['team']):
            raise HTTPBadRequest('Invalid event update', 'Event user must be part of the team')

        now = time.time()
        if event_summary['start'] < now - constants.GRACE_PERIOD:
            raise HTTPBadRequest('Invalid event update',
                                 'Editing events in the past not allowed')
        check_calendar_auth(event_summary['team'], req)

        update = 'UPDATE `event` SET %s WHERE link_id = %%(link_id)s' % update_cols
        data['link_id'] = link_id
        cursor.execute(update, data)
        if cursor.rowcount == 0:
            raise HTTPNotFound()
        create_audit({'old_event': event_summary, 'request_body': data},
                     event_summary['team'], EVENT_EDITED, req, cursor)

        cursor.execute('SELECT `user_id`, role_id FROM `event` WHERE `link_id` = %s', link_id)
        new_ev = cursor.fetchone()
        context = {'full_name': event_summary['full_name'], 'role': event_summary['role'], 'team': event_summary['team'],
                   'new_event': new_ev}
        create_notification(context, event_summary['team_id'], {event_summary['role_id'], new_ev['role_id']},
                            EVENT_EDITED, {event_summary['user_id'], new_ev['user_id']}, cursor,
                            start_time=event_summary['start'])
        connection.commit()
    finally:
        cursor.close()
        connection.close()
    resp.status = HTTP_204
