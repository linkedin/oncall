# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPError, HTTPBadRequest
from ujson import dumps as json_dumps
import time

from ...auth import login_required, check_calendar_auth_by_id
from ... import db, constants
from ...utils import load_json_body, user_in_team, create_notification, create_audit
from ...constants import EVENT_SUBSTITUTED


@login_required
def on_post(req, resp):
    """
    Override/substitute existing events. For example, if the current on-call is unexpectedly busy from 3-4, another
    user can override that event for that time period and take over the shift. Override may delete or edit
    existing events, and may create new events. The API's response contains the information for all undeleted
    events that were passed in the event_ids param, along with the events created by the override.

    Params:
        - **start**: Start time for the event substitution
        - **end**: End time for event substitution
        - **event_ids**: List of event ids to override
        - **user**: User who will be taking over

    **Example request:**

    .. sourcecode:: http

        POST api/v0/events/override   HTTP/1.1
        Content-Type: application/json

        {
            "start": 1493677400,
            "end": 1493678400,
            "event_ids": [1],
            "user": "jdoe"
        }

    **Example response:**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "end": 1493678400,
                "full_name": "John Doe",
                "id": 3,
                "role": "primary",
                "start": 1493677400,
                "team": "team-foo",
                "user": "jdoe"
            }
        ]

    """
    data = load_json_body(req)
    event_ids = data['event_ids']
    start = data['start']
    end = data['end']
    user = data['user']

    get_events_query = '''SELECT `start`, `end`, `id`, `schedule_id`, `user_id`, `role_id`, `team_id`
                          FROM `event` WHERE `id` IN %s'''
    insert_event_query = 'INSERT INTO `event`(`start`, `end`, `user_id`, `team_id`, `role_id`)' \
                         'VALUES (%(start)s, %(end)s, %(user_id)s, %(team_id)s, %(role_id)s)'
    event_return_query = '''SELECT `event`.`start`, `event`.`end`, `event`.`id`, `role`.`name` AS `role`,
                                `team`.`name` AS `team`, `user`.`name` AS `user`, `user`.`full_name`
                            FROM `event` JOIN `role` ON `event`.`role_id` = `role`.`id`
                                JOIN `team` ON `event`.`team_id` = `team`.`id`
                                JOIN `user` ON `event`.`user_id` = `user`.`id`
                            WHERE `event`.`id` IN %s'''

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    try:
        cursor.execute(get_events_query, (event_ids,))
        events = cursor.fetchall()
        now = time.time()

        cursor.execute('SELECT `id` FROM `user` WHERE `name` = %s', user)
        user_id = cursor.fetchone()
        if not (events and user_id):
            raise HTTPBadRequest('Invalid name or list of events')
        else:
            user_id = user_id['id']
            team_id = events[0]['team_id']

        check_calendar_auth_by_id(team_id, req)
        # Check that events are not in the past
        if start < now - constants.GRACE_PERIOD:
            raise HTTPBadRequest('Invalid override request', 'Cannot edit events in the past')
        # Check that events are from the same team
        if any([ev['team_id'] != team_id for ev in events]):
            raise HTTPBadRequest('Invalid override request', 'Events must be from the same team')
        # Check override user's membership in the team
        if not user_in_team(cursor, user_id, team_id):
            raise HTTPBadRequest('Invalid override request', 'Substituting user must be part of the team')
        # Check events have the same role
        if len(set([ev['role_id'] for ev in events])) > 1:
            raise HTTPBadRequest('Invalid override request', 'events must have the same role')
        # Check events have same user
        if len(set([ev['user_id'] for ev in events])) > 1:
            raise HTTPBadRequest('Invalid override request', 'events must have the same role')

        edit_start = []
        edit_end = []
        delete = []
        split = []
        events = sorted(events, key=lambda x: x['start'])

        # Truncate start/end if needed
        start = max(events[0]['start'], start)
        end = min(max(e['end'] for e in events), end)

        for idx, e in enumerate(events):
            # Check for consecutive events
            if idx != 0 and e['start'] != events[idx - 1]['end']:
                raise HTTPBadRequest('Invalid override request', 'events must be consecutive')

            # Sort events into lists according to how they need to be edited
            if start <= e['start'] and end >= e['end']:
                delete.append(e)
            elif start > e['start'] and start < e['end'] <= end:
                edit_end.append(e)
            elif start <= e['start'] < end and end < e['end']:
                edit_start.append(e)
            elif start > e['start'] and end < e['end']:
                split.append(e)
            else:
                raise HTTPBadRequest('Invalid override request', 'events must overlap with override time range')

        # Edit events
        if edit_start:
            ids = [e['id'] for e in edit_start]
            cursor.execute('UPDATE `event` SET `start` = %s WHERE `id` IN %s', (end, ids))
        if edit_end:
            ids = [e['id'] for e in edit_end]
            cursor.execute('UPDATE `event` SET `end` = %s WHERE `id` IN %s', (start, ids))
        if delete:
            ids = [e['id'] for e in delete]
            cursor.execute('DELETE FROM `event` WHERE `id` IN %s', (ids,))
        if split:
            create = []
            for e in split:
                left_event = e.copy()
                right_event = e.copy()
                left_event['end'] = start
                right_event['start'] = end
                create.append(left_event)
                create.append(right_event)

            ids = []
            # Create left/right events
            for e in create:
                cursor.execute(insert_event_query, e)
                ids.append(cursor.lastrowid)
                event_ids.append(cursor.lastrowid)

            # Delete the split event
            ids = [e['id'] for e in split]
            cursor.execute('DELETE FROM `event` WHERE `id` IN %s', (ids,))

        # Insert new override event
        override_event = {
            'start': start,
            'end': end,
            'role_id': events[0]['role_id'],
            'team_id': events[0]['team_id'],
            'user_id': user_id
        }
        cursor.execute('''INSERT INTO `event`(`start`, `end`, `user_id`, `team_id`, `role_id`)
                          VALUES (%(start)s, %(end)s, %(user_id)s, %(team_id)s, %(role_id)s)''',
                       override_event)
        event_ids.append(cursor.lastrowid)

        cursor.execute(event_return_query, (event_ids,))
        ret_data = cursor.fetchall()
        cursor.execute('SELECT full_name, id FROM user WHERE id IN %s', ((user_id, events[0]['user_id']),))
        full_names = {row['id']: row['full_name'] for row in cursor}
        context = {'full_name_0': full_names[user_id], 'full_name_1': full_names[events[0]['user_id']],
                   'role': ret_data[0]['role'], 'team': ret_data[0]['team']}
        create_notification(context, events[0]['team_id'], [events[0]['role_id']], EVENT_SUBSTITUTED,
                            [user_id, events[0]['user_id']], cursor, start_time=start, end_time=end)
        create_audit({'new_events': ret_data, 'request_body': data}, ret_data[0]['team'],
                     EVENT_SUBSTITUTED, req, cursor)
        resp.body = json_dumps(ret_data)
    except HTTPError:
        raise
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()
