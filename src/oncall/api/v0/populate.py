# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ...utils import load_json_body
from ...auth import check_team_auth, login_required
from schedules import get_schedules
from ...bin.scheduler import calculate_future_events, epoch_from_datetime, \
    create_events, find_least_active_available_user_id, get_period_len, set_last_epoch
from datetime import datetime, timedelta
from falcon import HTTPBadRequest
from pytz import timezone, utc


@login_required
def on_post(req, resp, schedule_id):
    """
    Run the scheduler on demand from a given point in time. Deletes existing schedule events if applicable.
    Given the ``start`` param, this will find the first schedule start time after ``start``, then populate out
    to the schedule's auto_populate_threshold. It will also clear the calendar of any events associated
    with the chosen schedule from the start of the first event it created onward. For example, if `start`
    is Monday, May 1 and the chosen schedule starts on Wednesday, this will create events starting from
    Wednesday, May 3, and delete any events that start after May 3 that are associated with the schedule.

    **Example request:**

    .. sourcecode:: http

        POST api/v0/   HTTP/1.1
        Content-Type: application/json

    :statuscode 200: Successful populate
    :statuscode 400: Validation checks failed
    """
    # TODO: add images to docstring because it doesn't make sense
    data = load_json_body(req)
    start_time = data['start']
    start_dt = datetime.fromtimestamp(start_time, utc)
    start_epoch = epoch_from_datetime(start_dt)

    # Get schedule info
    schedule = get_schedules({'id': schedule_id})[0]
    role_id = schedule['role_id']
    team_id = schedule['team_id']
    roster_id = schedule['roster_id']
    first_event_start = min(schedule['events'], key=lambda x: x['start'])['start']
    period = get_period_len(schedule)
    handoff = start_epoch + timedelta(seconds=first_event_start)
    handoff = timezone(schedule['timezone']).localize(handoff)

    # Start scheduling from the next occurrence of the hand-off time.
    if start_dt > handoff:
        start_epoch += timedelta(weeks=period)
        handoff += timedelta(weeks=period)
    if handoff < utc.localize(datetime.utcnow()):
        raise HTTPBadRequest('Invalid populate request', 'cannot populate starting in the past')

    check_team_auth(schedule['team'], req)

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    future_events, last_epoch = calculate_future_events(schedule, cursor, start_epoch)
    set_last_epoch(schedule_id, last_epoch, cursor)

    # Delete existing events from the start of the first event
    future_events = [filter(lambda x: x['start'] >= start_time, evs) for evs in future_events]
    future_events = filter(lambda x: x != [], future_events)
    if future_events:
        first_event_start = min(future_events[0], key=lambda x: x['start'])['start']
        cursor.execute('DELETE FROM event WHERE schedule_id = %s AND start >= %s', (schedule_id, first_event_start))

    # Create events in the db, associating a user to them
    for epoch in future_events:
        user_id = find_least_active_available_user_id(team_id, role_id, roster_id, epoch, cursor)
        if not user_id:
            continue
        create_events(team_id, schedule['id'], user_id, epoch, role_id, cursor)

    connection.commit()
    cursor.close()
    connection.close()
