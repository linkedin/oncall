# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPError, HTTPBadRequest, HTTPNotFound
import time

from ... import db, constants
from ...utils import load_json_body, create_notification, create_audit
from ...auth import login_required, check_calendar_auth_by_id
from ...constants import EVENT_SWAPPED


@login_required
def on_post(req, resp):
    """
    Swap events. Takes an object specifying the 2 events to be swapped. Swap can
    take either single events or event sets, depending on the value of the
    "linked" attribute. If "linked" is True, the API interprets the "id"
    attribute as a link_id. Otherwise, it's assumed to be an event_id. Note
    that this allows swapping a single event with a linked event.

    **Example request**:

    .. sourcecode:: http

        POST api/v0/events/swap   HTTP/1.1
        Content-Type: application/json

        {
            "events":
            [
                {
                    "id": 1,
                    "linked": false
                },
                {
                    "id": "da515a45e2b2467bbdc9ea3bc7826d36",
                    "linked": true
                }
            ]
        }

    :statuscode 200: Successful swap
    :statuscode 400: Validation checks failed
    """
    data = load_json_body(req)

    try:
        ev_0, ev_1 = data['events']
    except ValueError:
        raise HTTPBadRequest('Invalid event swap request',
                             'Must provide 2 events')

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    try:
        # Accumulate event info for each link/event id
        events = [None, None]
        for i, ev in enumerate([ev_0, ev_1]):
            if not ev.get('id'):
                raise HTTPBadRequest('Invalid event swap request',
                                     'Invalid event id: %s' % ev.get('id'))
            if ev.get('linked'):
                cursor.execute('SELECT `id`, `start`, `end`, `team_id`, `user_id`, `role_id`, '
                               '`link_id` FROM `event` WHERE `link_id` = %s',
                               ev['id'])
            else:
                cursor.execute('SELECT `id`, `start`, `end`, `team_id`, `user_id`, `role_id`, '
                               '`link_id` FROM `event` WHERE `id` = %s',
                               ev['id'])
            if cursor.rowcount == 0:
                raise HTTPNotFound()
            events[i] = cursor.fetchall()

        events_0, events_1 = events
        events = events_0 + events_1
        # Validation checks
        now = time.time()
        if any([ev['start'] < now - constants.GRACE_PERIOD for ev in events]):
            raise HTTPBadRequest('Invalid event swap request',
                                 'Cannot edit events in the past')
        if len(set(ev['team_id'] for ev in events)) > 1:
            raise HTTPBadRequest('Event swap not allowed',
                                 'Swapped events must come from the same team')
        for ev_list in [events_0, events_1]:
            if len(set([ev['user_id'] for ev in ev_list])) != 1:
                raise HTTPBadRequest('', 'all linked events must have the same user')

        check_calendar_auth_by_id(events[0]['team_id'], req)

        # Swap event users
        change_queries = []
        for ev in (ev_0, ev_1):
            if not ev['linked']:
                # Break link if swapping a single event in a linked chain
                change_queries.append('UPDATE `event` SET `user_id` = %s, `link_id` = NULL WHERE `id` IN %s')
            else:
                change_queries.append('UPDATE `event` SET `user_id` = %s WHERE `id` IN %s')
        user_0 = events_0[0]['user_id']
        user_1 = events_1[0]['user_id']
        first_event_0 = min(events_0, key=lambda ev: ev['start'])
        first_event_1 = min(events_1, key=lambda ev: ev['start'])
        cursor.execute(change_queries[0],
                       (user_1, [e0['id'] for e0 in events_0]))
        cursor.execute(change_queries[1],
                       (user_0, [e1['id'] for e1 in events_1]))

        cursor.execute('SELECT id, full_name FROM user WHERE id IN %s',
                       ([user_0, user_1],))
        full_names = {row['id']: row['full_name'] for row in cursor}
        cursor.execute('SELECT name FROM team WHERE id = %s',
                       events[0]['team_id'])
        team_name = cursor.fetchone()['name']
        context = {
            'full_name_0': full_names[user_0],
            'full_name_1': full_names[user_1],
            'team': team_name
        }
        create_notification(context,
                            events[0]['team_id'],
                            {events_0[0]['role_id'], events_1[0]['role_id']},
                            EVENT_SWAPPED,
                            [user_0, user_1],
                            cursor,
                            start_time_0=first_event_0['start'],
                            start_time_1=first_event_1['start'])
        create_audit({'request_body': data,
                      'events_swapped': (events_0, events_1)},
                     team_name, EVENT_SWAPPED, req, cursor)
        connection.commit()

    except HTTPError:
        raise
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()
