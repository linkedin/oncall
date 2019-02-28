# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib.parse import unquote
from falcon import HTTP_201, HTTPError, HTTPBadRequest
from ujson import dumps as json_dumps

from ...utils import load_json_body
from ...auth import login_required, check_team_auth
from ... import db

HOUR = 60 * 60
WEEK = 24 * HOUR * 7
simple_ev_lengths = set([WEEK, 2 * WEEK])
simple_12hr_num_events = set([7, 14])

columns = {
    'id': '`schedule`.`id` as `id`',
    'roster': '`roster`.`name` as `roster`, `roster`.`id` AS `roster_id`',
    'auto_populate_threshold': '`schedule`.`auto_populate_threshold` as `auto_populate_threshold`',
    'role': '`role`.`name` as `role`, `role`.`id` AS `role_id`',
    'team': '`team`.`name` as `team`, `team`.`id` AS `team_id`',
    'events': '`schedule_event`.`start`, `schedule_event`.`duration`, `schedule`.`id` AS `schedule_id`',
    'advanced_mode': '`schedule`.`advanced_mode` AS `advanced_mode`',
    'timezone': '`team`.`scheduling_timezone` AS `timezone`',
    'scheduler': '`scheduler`.`name` AS `scheduler`'
}

all_columns = list(columns.keys())

constraints = {
    'id': '`schedule`.`id` = %s',
    'id__eq': '`schedule`.`id` = %s',
    'id__ge': '`schedule`.`id` >= %s',
    'id__gt': '`schedule`.`id` > %s',
    'id__le': '`schedule`.`id` <= %s',
    'id__lt': '`schedule`.`id` < %s',
    'id__ne': '`schedule`.`id` != %s',
    'name': '`roster`.`name` = %s',
    'name__contains': '`roster`.`name` LIKE CONCAT("%%", %s, "%%")',
    'name__endswith': '`roster`.`name` LIKE CONCAT("%%", %s)',
    'name__eq': '`roster`.`name` = %s',
    'name__startswith': '`roster`.`name` LIKE CONCAT(%s, "%%")',
    'role': '`role`.`name` = %s',
    'role__contains': '`role`.`name` LIKE CONCAT("%%", %s, "%%")',
    'role__endswith': '`role`.`name` LIKE CONCAT("%%", %s)',
    'role__eq': '`role`.`name` = %s',
    'role__startswith': '`role`.`name` LIKE CONCAT(%s, "%%")',
    'team': '`team`.`name` = %s',
    'team__contains': '`team`.`name` LIKE CONCAT("%%", %s, "%%")',
    'team__endswith': '`team`.`name` LIKE CONCAT("%%", %s)',
    'team__eq': '`team`.`name` = %s',
    'team__startswith': '`team`.`name` LIKE CONCAT(%s, "%%")',
    'team_id': '`schedule`.`team_id` = %s',
    'roster_id': '`schedule`.`roster_id` = %s'
}


def validate_simple_schedule(events):
    '''
    Return boolean whether a schedule can be represented in simple mode. Simple schedules can have:
    1. One event that is one week long
    2. One event that is two weeks long
    3. Seven events that are 12 hours long
    4. Fourteen events that are 12 hours long
    '''
    if len(events) == 1 and events[0]['duration'] in simple_ev_lengths:
        return True
    else:
        return len(events) in simple_12hr_num_events and all([ev['duration'] == 12 * HOUR for ev in events])


def get_schedules(filter_params, dbinfo=None, fields=None):
    """
    Helper function to get schedule data for a request.

    :param filter_params: dict mapping constraint keys with values. Valid constraints are
    defined in the global ``constraints`` dict.
    :param dbinfo: optional. If provided, defines (connection, cursor) to use in DB queries.
    Otherwise, this creates its own connection/cursor.
    :param fields: optional. If provided, defines which schedule fields to return. Valid
    fields are defined in the global ``columns`` dict. Defaults to all fields. Invalid
    fields raise a 400 Bad Request.
    :return:
    """
    events = False
    scheduler = False
    from_clause = ['`schedule`']

    if fields is None:
        fields = list(columns.keys())
    if any(f not in columns for f in fields):
        raise HTTPBadRequest('Bad fields', 'One or more invalid fields')
    if 'roster' in fields:
        from_clause.append('JOIN `roster` ON `roster`.`id` = `schedule`.`roster_id`')
    if 'team' in fields or 'timezone' in fields:
        from_clause.append('JOIN `team` ON `team`.`id` = `schedule`.`team_id`')
    if 'role' in fields:
        from_clause.append('JOIN `role` ON `role`.`id` = `schedule`.`role_id`')
    if 'scheduler' in fields:
        from_clause.append('JOIN `scheduler` ON `scheduler`.`id` = `schedule`.`scheduler_id`')
        scheduler = True
    if 'events' in fields:
        from_clause.append('LEFT JOIN `schedule_event` ON `schedule_event`.`schedule_id` = `schedule`.`id`')
        events = True

    if 'id' not in fields:
        fields.append('id')
    fields = list(map(columns.__getitem__, fields))
    cols = ', '.join(fields)
    from_clause = ' '.join(from_clause)

    connection_opened = False
    if dbinfo is None:
        connection = db.connect()
        connection_opened = True
        cursor = connection.cursor(db.DictCursor)
    else:
        connection, cursor = dbinfo

    where = ' AND '.join(constraints[key] % connection.escape(value)
                         for key, value in filter_params.items()
                         if key in constraints)
    query = 'SELECT %s FROM %s' % (cols, from_clause)
    if where:
        query = '%s WHERE %s' % (query, where)

    cursor.execute(query)
    data = cursor.fetchall()
    if scheduler and data:
        schedule_ids = {d['id'] for d in data}
        cursor.execute('''SELECT `schedule_id`, `user`.`name` FROM `schedule_order`
                          JOIN `user` ON `user_id` = `user`.`id`
                          WHERE `schedule_id` IN %s
                          ORDER BY `schedule_id`,`priority`, `user_id`''',
                       schedule_ids)
        orders = {}
        # Accumulate roster orders for schedule
        for row in cursor:
            schedule_id = row['schedule_id']
            if schedule_id not in orders:
                orders[schedule_id] = []
            orders[schedule_id].append(row['name'])
    if connection_opened:
        cursor.close()
        connection.close()

    # Format schedule events
    if events:
        # end result accumulator
        ret = {}
        for row in data:
            schedule_id = row.pop('schedule_id')
            # add data row into accumulator only if not already there
            if schedule_id not in ret:
                ret[schedule_id] = row
                ret[schedule_id]['events'] = []
            start = row.pop('start')
            duration = row.pop('duration')
            ret[schedule_id]['events'].append({'start': start, 'duration': duration})
        data = list(ret.values())

    if scheduler:
        for schedule in data:
            scheduler_data = {'name': schedule['scheduler']}
            if schedule['id'] in orders:
                scheduler_data['data'] = orders[schedule['id']]
            schedule['scheduler'] = scheduler_data
    return data


def insert_schedule_events(schedule_id, events, cursor):
    """
    Helper to insert schedule events for a schedule
    """
    insert_events = '''INSERT INTO `schedule_event` (`schedule_id`, `start`, `duration`)
                       VALUES (%(schedule)s, %(start)s, %(duration)s)'''
    # Merge consecutive events for db storage. This creates an equivalent, simpler
    # form of the schedule for the scheduler.
    raw_events = sorted(events, key=lambda e: e['start'])
    new_events = []
    for e in raw_events:
        if len(new_events) > 0 and e['start'] == new_events[-1]['start'] + new_events[-1]['duration']:
            new_events[-1]['duration'] += e['duration']
        else:
            new_events.append(e)
    for e in new_events:
        e['schedule'] = schedule_id
    cursor.executemany(insert_events, new_events)


def on_get(req, resp, team, roster):
    """
    Get schedules for a given roster. Information on schedule attributes is detailed
    in the schedules POST endpoint documentation. Schedules can be filtered with
    the following parameters passed in the query string:

    :query id: id of the schedule
    :query id__eq: id of the schedule
    :query id__gt: id greater than
    :query id__ge: id greater than or equal
    :query id__lt: id less than
    :query id__le: id less than or equal
    :query name: schedule name
    :query name__eq: schedule name
    :query name__contains: schedule name contains param
    :query name__startswith: schedule name starts with param
    :query name__endswith: schedule name ends with param
    :query role: schedule role name
    :query role__eq: schedule role name
    :query role__contains: schedule role name contains param
    :query role__startswith: schedule role name starts with param
    :query role__endswith: schedule role name ends with param
    :query team: schedule team name
    :query team__eq: schedule team name
    :query team__contains: schedule team name contains param
    :query team__startswith: schedule team name starts with param
    :query team__endswith: schedule team name ends with param
    :query team_id: id of the schedule's team
    :query roster_id: id of the schedule's roster


    **Example request**:

    .. sourcecode:: http

        GET /api/v0/teams/team-foo/rosters/roster-foo/schedules  HTTP/1.1
        Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "advanced_mode": 1,
                "auto_populate_threshold": 30,
                "events": [
                    {
                        "duration": 259200,
                        "start": 0
                    }
                ],
                "id": 2065,
                "role": "primary",
                "role_id": 1,
                "roster": "roster-foo",
                "roster_id": 2922,
                "team": "team-foo",
                "team_id": 2121,
                "timezone": "US/Pacific"
            }
        ]
    """
    team = unquote(team)
    roster = unquote(roster)
    fields = req.get_param_as_list('fields')
    if not fields:
        fields = all_columns

    params = req.params
    params['team'] = team
    params['roster'] = roster
    data = get_schedules(params, fields=fields)

    resp.body = json_dumps(data)


required_params = frozenset(['events', 'role', 'advanced_mode'])


@login_required
def on_post(req, resp, team, roster):
    '''
    Schedule create endpoint. Schedules are templates for the auto-scheduler to follow that define
    how it should populate a certain period of time. This template is followed repeatedly to
    populate events on a team's calendar. Schedules are associated with a roster, which defines
    the pool of users that the scheduler selects from. Similarly, the schedule's role indicates
    the role that the populated events shoud have. The ``auto_populate_threshold`` parameter
    defines how far into the future the scheduler populates.

    Finally, each schedule has a list of events, each defining ``start`` and ``duration``. ``start``
    represents an offset from Sunday at 00:00 in the team's scheduling timezone, in seconds. For
    example, denote DAY and HOUR as the number of seconds in a day/hour, respectively. An
    event with ``start`` of (DAY + 9 * HOUR) starts on Monday, at 9:00 am. Duration is also given
    in seconds.

    The scheduler will start at Sunday 00:00 in the team's scheduling timezone, choose a user,
    and populate events on the calendar according to the offsets defined in the events list.
    It then repeats this process, moving to the next Sunday 00:00 after the events it has
    created.

    ``advanced_mode`` acts as a hint to the frontend on how the schedule should be displayed,
    defining whether the advanced mode toggle on the schedule edit action should be set on or off.
    Because of how the frontend displays simple schedules, a schedule can only have advanced_mode = 0
    if its events have one of 4 formats:

    1. One event that is one week long
    2. One event that is two weeks long
    3. Seven events that are 12 hours long
    4. Fourteen events that are 12 hours long

    See below for sample JSON requests.

    Assume these schedules' team defines US/Pacific as its scheduling timezone.

    Weekly 7*24 shift that starts at Monday 6PM PST:

    .. code-block:: javascript

        {
            'role': 'primary'
            'auto_populate_threshold': 21,
            'events':[
                {'start': SECONDS_IN_A_DAY + 18 * SECONDS_IN_AN_HOUR,
                 'duration': SECONDS_IN_A_WEEK}
            ],
            'advanced_mode': 0
        }

    Weekly 7*12 shift that starts at Monday 8AM PST:

    .. code-block:: javascript

        {
            'role': 'oncall',
            'events':[
                {'start': SECONDS_IN_A_DAY + 8 * SECONDS_IN_AN_HOUR,
                 'duration': 12 * SECONDS_IN_AN_HOUR},
                {'start': 2 * SECONDS_IN_A_DAY + 8 * SECONDS_IN_AN_HOUR,
                 'duration': 12 * SECONDS_IN_AN_HOUR} ... *5 more*
            ],
            'advanced_mode': 1
        }

    **Example Request**

    .. sourcecode:: http

        POST /v0/teams/team-foo/rosters/roster-foo/schedules   HTTP/1.1
        Content-Type: application/json

        {
            "advanced_mode": 0,
            "auto_populate_threshold": "21",
            "events": [
                {
                    "duration": 604800,
                    "start": 129600
                }
            ],
            "role": "primary",
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 OK
        Content-Type: application/json

        {
            "id": 2221
        }

    :statuscode 201: Successful schedule create. Response contains created schedule's id.
    :statuscode 400: Missing required parameters
    :statuscode 422: Invalid roster specified
    '''
    data = load_json_body(req)
    data['team'] = unquote(team)
    data['roster'] = unquote(roster)
    check_team_auth(data['team'], req)
    missing_params = required_params - set(data.keys())
    if missing_params:
        raise HTTPBadRequest('invalid schedule',
                             'missing required parameters: %s' % ', '.join(missing_params))

    schedule_events = data.pop('events')
    for sev in schedule_events:
        if 'start' not in sev or 'duration' not in sev:
            raise HTTPBadRequest('invalid schedule',
                                 'schedule event requires both start and duration fields')

    if 'auto_populate_threshold' not in data:
        # default to autopopulate 3 weeks forward
        data['auto_populate_threshold'] = 21

    if 'scheduler' not in data:
        # default to "default" scheduling algorithm
        data['scheduler_name'] = 'default'
    else:
        data['scheduler_name'] = data['scheduler'].get('name', 'default')
        scheduler_data = data['scheduler'].get('data')

    if not data['advanced_mode']:
        if not validate_simple_schedule(schedule_events):
            raise HTTPBadRequest('invalid schedule', 'invalid advanced mode setting')

    insert_schedule = '''INSERT INTO `schedule` (`roster_id`,`team_id`,`role_id`,
                                                 `auto_populate_threshold`, `advanced_mode`, `scheduler_id`)
                         VALUES ((SELECT `roster`.`id` FROM `roster`
                                      JOIN `team` ON `roster`.`team_id` = `team`.`id`
                                      WHERE `roster`.`name` = %(roster)s AND `team`.`name` = %(team)s),
                                 (SELECT `id` FROM `team` WHERE `name` = %(team)s),
                                 (SELECT `id` FROM `role` WHERE `name` = %(role)s),
                                 %(auto_populate_threshold)s,
                                 %(advanced_mode)s,
                                 (SELECT `id` FROM `scheduler` WHERE `name` = %(scheduler_name)s))'''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    try:
        cursor.execute(insert_schedule, data)
        schedule_id = cursor.lastrowid
        insert_schedule_events(schedule_id, schedule_events, cursor)

        if data['scheduler_name'] == 'round-robin':
            params = [(schedule_id, name, idx) for idx, name in enumerate(scheduler_data)]
            cursor.executemany('''INSERT INTO `schedule_order` (`schedule_id`, `user_id`, `priority`)
                                  VALUES (%s, (SELECT `id` FROM `user` WHERE `name` = %s), %s)''',
                               params)
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'roster_id\' cannot be null':
            err_msg = 'roster "%s" not found' % roster
        elif err_msg == 'Column \'role_id\' cannot be null':
            err_msg = 'role not found'
        elif err_msg == 'Column \'scheduler_id\' cannot be null':
            err_msg = 'scheduler not found'
        elif err_msg == 'Column \'team_id\' cannot be null':
            err_msg = 'team "%s" not found' % team
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps({'id': schedule_id})
