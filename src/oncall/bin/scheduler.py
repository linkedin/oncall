#!/usr/bin/env python

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# -*- coding:utf-8 -*-

from __future__ import print_function

import sys
import time
from oncall.utils import gen_link_id
from datetime import datetime, timedelta
from pytz import timezone, utc

from oncall import db, utils
from oncall.api.v0.schedules import get_schedules

import logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-6s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

logging.getLogger('requests').setLevel(logging.WARN)

UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=utc)
SECONDS_IN_A_DAY = 24 * 60 * 60
SECONDS_IN_A_WEEK = SECONDS_IN_A_DAY * 7


def get_role_id(role_name, cursor):
    cursor.execute('SELECT `id` FROM `role` WHERE `name` = %s', role_name)
    role_id = cursor.fetchone()['id']
    return role_id


def get_schedule_last_event_end(schedule, cursor):
    cursor.execute('SELECT `end` FROM `event` WHERE `schedule_id` = %r ORDER BY `end` DESC LIMIT 1',
                   schedule['id'])
    if cursor.rowcount != 0:
        return cursor.fetchone()['end']
    else:
        return None


def get_schedule_last_epoch(schedule, cursor):
    cursor.execute('SELECT `last_epoch_scheduled` FROM `schedule` WHERE `id` = %s',
                   schedule['id'])
    if cursor.rowcount != 0:
        return cursor.fetchone()['last_epoch_scheduled']
    else:
        return None


def get_roster_user_ids(roster_id, cursor):
    cursor.execute('''
        SELECT `roster_user`.`user_id` FROM `roster_user`
        JOIN `user` ON `user`.`id` = `roster_user`.`user_id`
        WHERE `roster_user`.`in_rotation` = 1 AND `roster_user`.`roster_id` = %r
            AND `user`.`active` = TRUE''', roster_id)
    return [r['user_id'] for r in cursor]


def get_busy_user_by_event_range(user_ids, team_id, start, end, cursor):
    ''' Find which users have overlapping events for the same team in this time range'''
    cursor.execute('''
        SELECT `user_id`, COUNT(`id`) as `conflict_count` FROM `event`
        WHERE `user_id` in %s AND %r < `end` AND `start` < %r AND team_id = %s
        GROUP BY `user_id`
        ''', (user_ids, start, end, team_id))
    return [r['user_id'] for r in cursor.fetchall() if r['conflict_count'] > 0]


def find_least_active_user_id_by_team(user_ids, team_id, start_time, role_id, cursor):
    '''
    Of the people who have been oncall before, finds those who haven't been oncall for the longest. Start
    time refers to the start time of the event being created, so we don't accidentally look at future
    events when determining who was oncall in the past. Done on a per-role basis, so we don't take manager
    or vacation shifts into account
    '''
    cursor.execute('''
        SELECT `user_id`, MAX(`end`) AS `last_end` FROM `event`
        WHERE `team_id` = %s AND `user_id` IN %s AND `end` <= %s
        AND `role_id` = %s
        GROUP BY `user_id`
        ''', (team_id, user_ids, start_time, role_id))
    if cursor.rowcount != 0:
        # Grab user id with lowest last scheduled time
        return min(cursor.fetchall(), key=lambda x: x['last_end'])['user_id']
    else:
        return None


def find_new_user_in_roster(roster_id, team_id, start_time, role_id, cursor):
    '''
    Return roster users who haven't been scheduled for any event on this team's calendar for this schedule's role.
    Ignores events from other teams.
    '''
    query = '''
        SELECT DISTINCT `user`.`id` FROM `roster_user`
        JOIN `user` ON `user`.`id` = `roster_user`.`user_id` AND `roster_user`.`roster_id` = %s
        LEFT JOIN `event` ON `event`.`user_id` = `user`.`id` AND `event`.`team_id` = %s AND `event`.`end` <= %s
            AND `event`.`role_id` = %s
        WHERE `roster_user`.`in_rotation` = 1 AND `event`.`id` IS NULL
    '''
    cursor.execute(query, (roster_id, team_id, start_time, role_id))
    if cursor.rowcount != 0:
        logger.debug('Found new guy')
    return set(row['id'] for row in cursor)


def create_events(team_id, schedule_id, user_id, events, role_id, cursor):
    if len(events) == 1:
        [event] = events
        event_args = (team_id, schedule_id, event['start'], event['end'], user_id, role_id)
        logger.debug('inserting event: %s', event_args)
        query = '''
            INSERT INTO `event` (
                `team_id`, `schedule_id`, `start`, `end`, `user_id`, `role_id`
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )'''
        cursor.execute(query, event_args)
    else:
        link_id = gen_link_id()
        for event in events:
            event_args = (team_id, schedule_id, event['start'], event['end'], user_id, role_id, link_id)
            logger.debug('inserting event: %s', event_args)
            query = '''
                INSERT INTO `event` (
                    `team_id`, `schedule_id`, `start`, `end`, `user_id`, `role_id`, `link_id`
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )'''
            cursor.execute(query, event_args)


def set_last_epoch(schedule_id, last_epoch, cursor):
    cursor.execute('UPDATE `schedule` SET `last_epoch_scheduled` = %s WHERE `id` = %s',
                   (last_epoch, schedule_id))


# End of DB interactions

def weekday_from_schedule_time(schedule_time):
    '''Returns 0 for Monday, 1 for Tuesday...'''
    return (schedule_time / SECONDS_IN_A_DAY - 1) % 7


def epoch_from_datetime(dt):
    '''
    Given timezoned or naive datetime, returns a naive datetime for 00:00:00 on the
    first Sunday before the given date
    '''
    sunday = dt + timedelta(days=(-(dt.isoweekday() % 7)))
    epoch = sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    return epoch


def get_closest_epoch(dt):
    '''
    Given naive datetime, returns naive datetime of the closest epoch (Sunday midnight)
    '''
    dt = dt.replace(tzinfo=None)
    before_sunday = dt + timedelta(days=(-(dt.isoweekday() % 7)))
    before = before_sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    after_sunday = dt + timedelta(days=7 - dt.isoweekday())
    after = after_sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    before_diff = dt - before
    after_diff = after - dt
    if before_diff < after_diff:
        return before
    else:
        return after


def utc_from_naive_date(date, schedule):
    tz = timezone(schedule['timezone'])
    # Arbitrarily choose ambiguous/nonexistent dates to be in DST. Results in no gaps in a schedule given
    # a consistent arbitrary choice.
    date = (tz.localize(date, is_dst=1)).astimezone(utc)
    td = date - UNIX_EPOCH
    # Convert timedelta to seconds
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


def generate_events(schedule, schedule_events, epoch):
    generated = []
    for event in schedule_events:
        start = timedelta(seconds=event['start']) + epoch
        # Need to calculate naive end date to correct for DST
        end = timedelta(seconds=event['start'] + event['duration']) + epoch
        start = utc_from_naive_date(start, schedule)
        end = utc_from_naive_date(end, schedule)
        generated.append({'start': start, 'end': end})
    return generated


def get_period_len(schedule):
    '''
    Find schedule rotation period in weeks, rounded up
    '''
    events = schedule['events']
    first_event = min(events, key=lambda x: x['start'])
    end = max(e['start'] + e['duration'] for e in events)
    period = end - first_event['start']
    return ((period + SECONDS_IN_A_WEEK - 1) / SECONDS_IN_A_WEEK)


def calculate_future_events(schedule, cursor, start_epoch=None):
    period = get_period_len(schedule)

    # DEFINITION:
    # epoch: Sunday at 00:00:00 in the schedule's local timezone. This is our point of reference when
    #        populating events. Why not UTC? DST.

    # Find where to start scheduling
    if start_epoch is None:
        last_epoch_timestamp = get_schedule_last_epoch(schedule, cursor)

        # Handle new schedules, start scheduling from current week
        if last_epoch_timestamp is None:
            start_dt = datetime.fromtimestamp(time.time(), utc).astimezone(timezone(schedule['timezone']))
            next_epoch = epoch_from_datetime(start_dt)
        else:
            # Otherwise, find the next epoch (NOTE: can't assume that last_epoch_timestamp is Sunday 00:00:00 in the
            # schedule's timezone, because the scheduling timezone might have changed. Instead, find the closest
            # epoch and work from there)
            last_epoch_dt = datetime.fromtimestamp(last_epoch_timestamp, utc)
            localized_last_epoch = last_epoch_dt.astimezone(timezone(schedule['timezone']))
            next_epoch = get_closest_epoch(localized_last_epoch) + timedelta(days=7 * period)
    else:
        next_epoch = start_epoch

    cutoff_date = datetime.fromtimestamp(time.time(), utc) + timedelta(days=schedule['auto_populate_threshold'])
    cutoff_date = cutoff_date.replace(tzinfo=None)
    future_events = []
    # Start scheduling from the next epoch
    while cutoff_date > next_epoch:
        epoch_events = generate_events(schedule, schedule['events'], next_epoch)
        next_epoch += timedelta(days=7 * period)
        if epoch_events:
            future_events.append(epoch_events)
    # Return future events and the last epoch events were scheduled for.
    return future_events, utc_from_naive_date(next_epoch - timedelta(days=7 * period), schedule)


def find_least_active_available_user_id(team_id, role_id, roster_id, future_events, cursor):
    # find people without conflicting events
    # TODO: finer grain conflict checking
    user_ids = set(get_roster_user_ids(roster_id, cursor))
    if not user_ids:
        logger.info('Empty roster, skipping')
        return None
    logger.debug('filtering users: %s', user_ids)
    start = min([e['start'] for e in future_events])
    end = max([e['end'] for e in future_events])
    for uid in get_busy_user_by_event_range(user_ids, team_id, start, end, cursor):
        user_ids.remove(uid)
    if not user_ids:
        logger.info('All users have conflicting events, skipping...')
        return None
    new_user_ids = find_new_user_in_roster(roster_id, team_id, start, role_id, cursor)
    available_and_new = new_user_ids & user_ids
    if available_and_new:
        logger.info('Picking new and available user from %s', available_and_new)
        return available_and_new.pop()

    logger.debug('picking user between: %s, team: %s', user_ids, team_id)
    return find_least_active_user_id_by_team(user_ids, team_id, start, role_id, cursor)


def main():
    config = utils.read_config(sys.argv[1])
    db.init(config['db'])

    cycle_time = config.get('scheduler_cycle_time', 3600)

    while 1:
        connection = db.connect()
        db_cursor = connection.cursor(db.DictCursor)

        start = time.time()
        # Iterate through all teams
        db_cursor.execute('SELECT id, name, scheduling_timezone FROM team WHERE active = TRUE')
        teams = db_cursor.fetchall()
        for team in teams:
            team_id = team['id']
            # Get rosters for team
            db_cursor.execute('SELECT `id`, `name` FROM `roster` WHERE `team_id` = %s', team_id)
            rosters = db_cursor.fetchall()
            if db_cursor.rowcount == 0:
                continue
            logger.info('scheduling for team: %s', team['name'])
            events = []
            for roster in rosters:
                roster_id = roster['id']
                # Get schedules for each roster
                schedules = get_schedules({'team_id': team_id, 'roster_id': roster_id})
                for schedule in schedules:
                    if schedule['auto_populate_threshold'] <= 0:
                        continue
                    logger.info('\t\tschedule: %s', str(schedule['id']))
                    schedule['timezone'] = team['scheduling_timezone']
                    # Calculate events for schedule
                    future_events, last_epoch = calculate_future_events(schedule, db_cursor)
                    role_id = get_role_id(schedule['role'], db_cursor)
                    for epoch in future_events:
                        # Add (start_time, schedule_id, role_id, roster_id, epoch_events) to events
                        events.append((min([ev['start'] for ev in epoch]), schedule['id'], role_id, roster_id, epoch))
                    set_last_epoch(schedule['id'], last_epoch, db_cursor)
            # Create events in the db, associating a user to them
            # Iterate through events in order of start time to properly assign users
            for event_info in sorted(events, key=lambda x: x[0]):
                _, schedule_id, role_id, roster_id, epoch = event_info
                user_id = find_least_active_available_user_id(team_id, role_id, roster_id, epoch, db_cursor)
                if not user_id:
                    logger.info('Failed to find available user')
                    continue
                logger.info('Found user: %s', user_id)
                create_events(team_id, schedule_id, user_id, epoch, role_id, db_cursor)
            connection.commit()
        # Sleep until next time
        sleep_time = cycle_time - (time.time() - start)
        if sleep_time > 0:
            logger.info('Sleeping for %s seconds' % sleep_time)
            time.sleep(cycle_time - (time.time() - start))
        else:
            logger.info('Schedule loop took %s seconds, skipping sleep' % (time.time() - start))

        db_cursor.close()
        connection.close()


if __name__ == '__main__':
    main()
