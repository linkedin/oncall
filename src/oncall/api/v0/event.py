# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import time
from ujson import dumps as json_dumps
from falcon import HTTPNotFound, HTTPBadRequest, HTTPUnauthorized

from ...auth import login_required, check_calendar_auth, check_team_auth
from ... import db, constants
from ...utils import (
    load_json_body, user_in_team_by_name, create_notification, create_audit
)
from ...constants import EVENT_DELETED, EVENT_EDITED

from .events import columns, all_columns

update_columns = {
    'start': '`start`=%(start)s',
    'end': '`end`=%(end)s',
    'role': '`role_id`=(SELECT `id` FROM `role` WHERE `name`=%(role)s)',
    'user': '`user_id`=(SELECT `id` FROM `user` WHERE `name`=%(user)s)',
    'note': '`note`=%(note)s'
}


def on_get(req, resp, event_id):
    '''
    Get event by id.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/events/1234 HTTP/1.1
        Host: example.com

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "end": 1428336000,
            "full_name": "John Doe",
            "id": 1234,
            "link_id": null,
            "role": "primary",
            "schedule_id": 4321,
            "start": 1427731200,
            "team": "team-foo",
            "user": "jdoe"
        }

    :statuscode 200: no error
    :statuscode 404: Event not found
    '''
    fields = req.get_param_as_list('fields', transform=columns.__getitem__)
    cols = ', '.join(fields) if fields else all_columns
    query = '''SELECT %s FROM `event`
               JOIN `user` ON `user`.`id` = `event`.`user_id`
               JOIN `team` ON `team`.`id` = `event`.`team_id`
               JOIN `role` ON `role`.`id` = `event`.`role_id`
               WHERE `event`.`id` = %%s''' % cols

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(query, event_id)
    data = cursor.fetchone()
    num_found = cursor.rowcount
    cursor.close()
    connection.close()
    if num_found == 0:
        raise HTTPNotFound()
    resp.body = json_dumps(data)


@login_required
def on_put(req, resp, event_id):
    """
    Update an event by id; anyone can update any event within the team

    **Example request:**

    .. sourcecode:: http

        PUT /api/v0/events/1234 HTTP/1.1
        Content-Type: application/json

        {
            "start": 1428336000,
            "end": 1428338000,
            "user": "asmith",
            "role": "secondary"
        }

    :statuscode 200: Successful update

    """
    data = load_json_body(req)

    if 'end' in data and 'start' in data and data['start'] >= data['end']:
        raise HTTPBadRequest('Invalid event update', 'Event must start before it ends')

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
                `event`.`note`,
                `team`.`name` AS `team`,
                `role`.`name` AS `role`,
                `user`.`name` AS `user`,
                `user`.`full_name`,
                `event`.`team_id`
            FROM `event`
            JOIN `team` ON `event`.`team_id` = `team`.`id`
            JOIN `role` ON `event`.`role_id` = `role`.`id`
            JOIN `user` ON `event`.`user_id` = `user`.`id`
            WHERE `event`.`id`=%s''', event_id)
        event_data = cursor.fetchone()
        if not event_data:
            raise HTTPNotFound()
        new_event = {}
        for col in update_columns:
            new_event[col] = data.get(col, event_data[col])
        now = time.time()
        if event_data['start'] < now - constants.GRACE_PERIOD or data['start'] < now - constants.GRACE_PERIOD:
            # Make an exception for editing event end times
            if not (all(event_data[key] == new_event[key] for key in ('role', 'start', 'user')) and
                    data['end'] > now):
                # Allow admins to edit in the past. If unauthorized for this action, return 400
                try:
                    check_team_auth(event_data['team'], req)
                except HTTPUnauthorized:
                    raise HTTPBadRequest('Invalid event update',
                                         'Editing events in the past not allowed')

        check_calendar_auth(event_data['team'], req)
        if not user_in_team_by_name(cursor, new_event['user'], event_data['team']):
            raise HTTPBadRequest('Invalid event update', 'Event user must be part of the team')

        update_cols += ', `link_id` = NULL'
        update = 'UPDATE `event` SET ' + update_cols + (' WHERE `id`=%d' % int(event_id))
        cursor.execute(update, data)

        # create audit log
        new_event = ', '.join('%s: %s' % (key, data[key]) for key in data)
        create_audit({'old_event': event_data, 'request_body': data},
                     event_data['team'], EVENT_EDITED, req, cursor)

        cursor.execute('SELECT `user_id`, role_id FROM `event` WHERE `id` = %s', event_data['id'])
        new_ev_data = cursor.fetchone()
        context = {'full_name': event_data['full_name'], 'role': event_data['role'], 'team': event_data['team'],
                   'new_event': new_event}
        create_notification(context, event_data['team_id'], {event_data['role_id'], new_ev_data['role_id']},
                            EVENT_EDITED, {event_data['user_id'], new_ev_data['user_id']}, cursor,
                            start_time=event_data['start'])
    except:
        raise
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()


@login_required
def on_delete(req, resp, event_id):
    """
    Delete an event by id, anyone on the team can delete that team's events

    **Example request:**

    .. sourcecode:: http

       DELETE /api/v0/events/1234 HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 403: Delete not allowed; logged in user is not a team member
    :statuscode 404: Event not found
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
                          WHERE `event`.`id` = %s''', event_id)
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            raise HTTPNotFound()
        ev = cursor.fetchone()
        check_calendar_auth(ev['team'], req)
        if ev['start'] < time.time() - constants.GRACE_PERIOD:
            raise HTTPBadRequest('Invalid event update',
                                 'Deleting events in the past not allowed')

        cursor.execute('DELETE FROM `event` WHERE `id`=%s', event_id)

        context = {'team': ev['team'], 'full_name': ev['full_name'], 'role': ev['role']}
        create_notification(context, ev['team_id'], [ev['role_id']], EVENT_DELETED, [ev['user_id']], cursor,
                            start_time=ev['start'])
        create_audit({'old_event': ev}, ev['team'], EVENT_DELETED, req, cursor)

        connection.commit()
    finally:
        cursor.close()
        connection.close()
