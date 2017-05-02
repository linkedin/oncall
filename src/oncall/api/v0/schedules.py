# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote
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
    'timezone': '`team`.`scheduling_timezone` AS `timezone`'
}

all_columns = columns.keys()

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
    Get schedule data for a request
    """
    events = False
    from_clause = ['`schedule`']

    if fields is None:
        fields = columns.keys()
    if any(f not in columns for f in fields):
        raise HTTPBadRequest('Bad fields', 'One or more invalid fields')
    if 'roster' in fields:
        from_clause.append('JOIN `roster` ON `roster`.`id` = `schedule`.`roster_id`')
    if 'team' in fields or 'timezone' in fields:
        from_clause.append('JOIN `team` ON `team`.`id` = `schedule`.`team_id`')
    if 'role' in fields:
        from_clause.append('JOIN `role` ON `role`.`id` = `schedule`.`role_id`')
    if 'events' in fields:
        from_clause.append('LEFT JOIN `schedule_event` ON `schedule_event`.`schedule_id` = `schedule`.`id`')
        events = True

    fields = map(columns.__getitem__, fields)
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
                         for key, value in filter_params.iteritems()
                         if key in constraints)
    query = 'SELECT %s FROM %s' % (cols, from_clause)
    if where:
        query = '%s WHERE %s' % (query, where)

    cursor.execute(query)
    data = cursor.fetchall()
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
        data = ret.values()
    return data


def insert_schedule_events(schedule_id, events, cursor):
    insert_events = '''INSERT INTO `schedule_event` (`schedule_id`, `start`, `duration`)
                       VALUES (%(schedule)s, %(start)s, %(duration)s)'''
    # Merge consecutive events for db storage
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
    See below for sample JSON requests.

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

    if not data['advanced_mode']:
        if not validate_simple_schedule(schedule_events):
            raise HTTPBadRequest('invalid schedule', 'invalid advanced mode setting')

    insert_schedule = '''INSERT INTO `schedule` (`roster_id`,`team_id`,`role_id`,
                                                 `auto_populate_threshold`, `advanced_mode`)
                         VALUES ((SELECT `roster`.`id` FROM `roster`
                                      JOIN `team` ON `roster`.`team_id` = `team`.`id`
                                      WHERE `roster`.`name` = %(roster)s AND `team`.`name` = %(team)s),
                                 (SELECT `id` FROM `team` WHERE `name` = %(team)s),
                                 (SELECT `id` FROM `role` WHERE `name` = %(role)s),
                                 %(auto_populate_threshold)s,
                                 %(advanced_mode)s)'''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    try:
        cursor.execute(insert_schedule, data)
        schedule_id = cursor.lastrowid
        insert_schedule_events(schedule_id, schedule_events, cursor)
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'roster_id\' cannot be null':
            err_msg = 'roster "%s" not found' % roster
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)

    connection.commit()
    cursor.close()
    connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps({'id': schedule_id})
