from datetime import datetime, timedelta
from pytz import timezone, utc
from oncall.utils import gen_link_id
from falcon import HTTPBadRequest
from ujson import dumps as json_dumps
import time
import logging
import operator

logger = logging.getLogger()

UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=utc)
SECONDS_IN_A_DAY = 24 * 60 * 60
SECONDS_IN_A_WEEK = SECONDS_IN_A_DAY * 7

columns = {
    'id': '`temp_event`.`id` as `id`',
    'start': '`temp_event`.`start` as `start`',
    'end': '`temp_event`.`end` as `end`',
    'role': '`role`.`name` as `role`',
    'team': '`team`.`name` as `team`',
    'user': '`user`.`name` as `user`',
    'full_name': '`user`.`full_name` as `full_name`',
    'schedule_id': '`temp_event`.`schedule_id`',
    'link_id': '`temp_event`.`link_id`',
    'note': '`temp_event`.`note`',
}

constraints = {
    'start__lt': '`temp_event`.`start` < %s',
    'end__ge': '`temp_event`.`end` >= %s',
    'team__eq': '`team`.`name` = %s',
}

all_columns = ', '.join(columns.values())


class Scheduler(object):
    def __init__(self):
        pass

    # DB interactions
    def get_role_id(self, role_name, cursor):
        cursor.execute('SELECT `id` FROM `role` WHERE `name` = %s', role_name)
        role_id = cursor.fetchone()['id']
        return role_id

    def get_schedule_last_event_end(self, schedule, cursor, table_name='event'):
        query = 'SELECT `end` FROM `%s` WHERE `schedule_id` = %%r ORDER BY `end` DESC LIMIT 1' % table_name
        cursor.execute(query, schedule['id'])
        if cursor.rowcount != 0:
            return cursor.fetchone()['end']
        else:
            return None

    def get_schedule_last_epoch(self, schedule, cursor):
        cursor.execute('SELECT `last_epoch_scheduled` FROM `schedule` WHERE `id` = %s',
                       schedule['id'])
        if cursor.rowcount != 0:
            return cursor.fetchone()['last_epoch_scheduled']
        else:
            return None

    def get_roster_user_ids(self, roster_id, cursor):
        cursor.execute('''
            SELECT `roster_user`.`user_id` FROM `roster_user`
            JOIN `user` ON `user`.`id` = `roster_user`.`user_id`
            WHERE `roster_user`.`in_rotation` = 1 AND `roster_user`.`roster_id` = %r
                AND `user`.`active` = TRUE''', roster_id)
        return [r['user_id'] for r in cursor]

    def get_busy_user_by_event_range(self, user_ids, team_id, events, cursor, table_name='event'):
        ''' Find which users have overlapping events for the same team in this time range'''
        query_params = [user_ids]
        range_check = []
        for e in events:
            range_check.append('(%s < `end` AND `start` < %s)')
            query_params += [e['start'], e['end']]

        cursor.execute('''SELECT `subscription_id`, `role_id`
                          FROM `team_subscription`
                          WHERE `team_id` = %s''',
                       team_id)
        subscriptions = cursor.fetchall()
        team_check = ['team_id = %s']
        query_params.append(team_id)
        for sub in subscriptions:
            team_check.append('(team_id = %s AND role_id = %s)')
            query_params += [sub['subscription_id'], sub['role_id']]

        query = '''
                SELECT DISTINCT `user_id` FROM `%s`
                WHERE `user_id` in %%s AND (%s) AND (%s or `role_id`= (SELECT `id` FROM `role` WHERE `name` = 'vacation'))
                ''' % (table_name, ' OR '.join(range_check), ' OR '.join(team_check))

        cursor.execute(query, query_params)
        return [r['user_id'] for r in cursor.fetchall()]

    def find_least_active_user_id_by_team(self, user_ids, team_id, start_time, role_id, cursor, table_name='event'):
        '''
        Of the people who have been oncall before, finds those who haven't been oncall for the longest. Start
        time refers to the start time of the event being created, so we don't accidentally look at future
        events when determining who was oncall in the past. Done on a per-role basis, so we don't take manager
        or vacation shifts into account
        '''
        query = '''
            SELECT `user_id`, MAX(`end`) AS `last_end` FROM `%s`
            WHERE `team_id` = %%s AND `user_id` IN %%s AND `end` <= %%s
            AND `role_id` = %%s
            GROUP BY `user_id`
            ''' % table_name

        cursor.execute(query, (team_id, user_ids, start_time, role_id))
        if cursor.rowcount != 0:
            # Grab user id with lowest last scheduled time
            return min(cursor.fetchall(), key=operator.itemgetter('last_end'))['user_id']
        else:
            return None

    def find_new_user_in_roster(self, roster_id, team_id, start_time, role_id, cursor, table_name='event'):
        '''
        Return roster users who haven't been scheduled for any event on this team's calendar for this schedule's role.
        Ignores events from other teams.
        '''
        query = '''
            SELECT DISTINCT `user`.`id` FROM `roster_user`
            JOIN `user` ON `user`.`id` = `roster_user`.`user_id` AND `roster_user`.`roster_id` = %%s
            LEFT JOIN `%s` ON `%s`.`user_id` = `user`.`id` AND `%s`.`team_id` = %%s AND `%s`.`end` <= %%s
                AND `%s`.`role_id` = %%s
            WHERE `roster_user`.`in_rotation` = 1 AND `%s`.`id` IS NULL
        ''' % (table_name, table_name, table_name, table_name, table_name, table_name)

        cursor.execute(query, (roster_id, team_id, start_time, role_id))
        if cursor.rowcount != 0:
            logger.debug('Found new guy')
        return {row['id'] for row in cursor}

    def create_events(self, team_id, schedule_id, user_id, events, role_id, cursor, table_name='event', skip_match=True):
        if len(events) == 0:
            return
        # Skip creating this epoch of events if matching events exist
        if skip_match:
            matching = ' OR '.join(['(start = %s AND end = %s AND role_id = %s AND team_id = %s)'] * len(events))
            query_params = []

            for ev in events:
                query_params += [ev['start'], ev['end'], role_id, team_id]

            query = 'SELECT COUNT(*) AS num_events FROM %s WHERE %s' % (table_name, matching)

            cursor.execute(query, query_params)
            if cursor.fetchone()['num_events'] == len(events):
                return

        if len(events) == 1:
            [event] = events
            event_args = (team_id, schedule_id, event['start'], event['end'], user_id, role_id)
            logger.debug('inserting event: %s', event_args)
            query = '''
                INSERT INTO `%s` (
                    `team_id`, `schedule_id`, `start`, `end`, `user_id`, `role_id`
                ) VALUES (
                    %%s, %%s, %%s, %%s, %%s, %%s
                )''' % table_name
            cursor.execute(query, event_args)
        else:
            link_id = gen_link_id()
            for event in events:
                event_args = (team_id, schedule_id, event['start'], event['end'], user_id, role_id, link_id)
                logger.debug('inserting event: %s', event_args)
                query = '''
                    INSERT INTO `%s` (
                        `team_id`, `schedule_id`, `start`, `end`, `user_id`, `role_id`, `link_id`
                    ) VALUES (
                        %%s, %%s, %%s, %%s, %%s, %%s, %%s
                    )''' % table_name
                cursor.execute(query, event_args)

    def set_last_epoch(self, schedule_id, last_epoch, cursor):
        cursor.execute('UPDATE `schedule` SET `last_epoch_scheduled` = %s WHERE `id` = %s',
                       (last_epoch, schedule_id))

    # End of DB interactions
    # Epoch/weekday/time helpers

    def weekday_from_schedule_time(self, schedule_time):
        '''Returns 0 for Monday, 1 for Tuesday...'''
        return (schedule_time // SECONDS_IN_A_DAY - 1) % 7

    def epoch_from_datetime(self, dt):
        '''
        Given timezoned or naive datetime, returns a naive datetime for 00:00:00 on the
        first Sunday before the given date
        '''
        sunday = dt + timedelta(days=(-(dt.isoweekday() % 7)))
        epoch = sunday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        return epoch

    def get_closest_epoch(self, dt):
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

    def utc_from_naive_date(self, date, schedule):
        tz = timezone(schedule['timezone'])
        # Arbitrarily choose ambiguous/nonexistent dates to be in DST. Results in no gaps in a schedule given
        # a consistent arbitrary choice.
        date = (tz.localize(date, is_dst=1)).astimezone(utc)
        td = date - UNIX_EPOCH
        # Convert timedelta to seconds
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) // 10 ** 6

    # End time helpers

    def generate_events(self, schedule, schedule_events, epoch):
        generated = []
        for event in schedule_events:
            start = timedelta(seconds=event['start']) + epoch
            # Need to calculate naive end date to correct for DST
            end = timedelta(seconds=event['start'] + event['duration']) + epoch
            start = self.utc_from_naive_date(start, schedule)
            end = self.utc_from_naive_date(end, schedule)
            generated.append({'start': start, 'end': end})
        return generated

    def get_period_len(self, schedule):
        '''
        Find schedule rotation period in weeks, rounded up
        '''
        events = schedule['events']
        first_event = min(events, key=operator.itemgetter('start'))
        end = max(e['start'] + e['duration'] for e in events)
        period = end - first_event['start']
        return ((period + SECONDS_IN_A_WEEK - 1) // SECONDS_IN_A_WEEK)

    def calculate_future_events(self, schedule, cursor, start_epoch=None):
        period = self.get_period_len(schedule)

        # DEFINITION:
        # epoch: Sunday at 00:00:00 in the schedule's local timezone. This is our point of reference when
        #        populating events. Why not UTC? DST.

        # Find where to start scheduling
        if start_epoch is None:
            last_epoch_timestamp = self.get_schedule_last_epoch(schedule, cursor)

            # Handle new schedules, start scheduling from current week
            if last_epoch_timestamp is None:
                start_dt = datetime.fromtimestamp(time.time(), utc).astimezone(timezone(schedule['timezone']))
                next_epoch = self.epoch_from_datetime(start_dt)
            else:
                # Otherwise, find the next epoch (NOTE: can't assume that last_epoch_timestamp is Sunday 00:00:00 in the
                # schedule's timezone, because the scheduling timezone might have changed. Instead, find the closest
                # epoch and work from there)
                last_epoch_dt = datetime.fromtimestamp(last_epoch_timestamp, utc)
                localized_last_epoch = last_epoch_dt.astimezone(timezone(schedule['timezone']))
                next_epoch = self.get_closest_epoch(localized_last_epoch) + timedelta(days=7 * period)
        else:
            next_epoch = start_epoch

        cutoff_date = datetime.fromtimestamp(time.time(), utc) + timedelta(days=schedule['auto_populate_threshold'])
        cutoff_date = cutoff_date.replace(tzinfo=None)
        future_events = []
        # Start scheduling from the next epoch
        while cutoff_date > next_epoch:
            epoch_events = self.generate_events(schedule, schedule['events'], next_epoch)
            next_epoch += timedelta(days=7 * period)
            if epoch_events:
                future_events.append(epoch_events)
        # Return future events and the last epoch events were scheduled for.
        return future_events, self.utc_from_naive_date(next_epoch - timedelta(days=7 * period), schedule)

    def find_next_user_id(self, schedule, future_events, cursor, table_name='event'):
        team_id = schedule['team_id']
        role_id = schedule['role_id']
        roster_id = schedule['roster_id']
        # find people without conflicting events
        # TODO: finer grain conflict checking
        user_ids = set(self.get_roster_user_ids(roster_id, cursor))
        if not user_ids:
            logger.info('Empty roster, skipping')
            return None
        logger.debug('filtering users: %s', user_ids)
        start = min([e['start'] for e in future_events])
        for uid in self.get_busy_user_by_event_range(user_ids, team_id, future_events, cursor, table_name):
            user_ids.remove(uid)
        if not user_ids:
            logger.info('All users have conflicting events, skipping...')
            return None
        new_user_ids = self.find_new_user_in_roster(roster_id, team_id, start, role_id, cursor, table_name)
        available_and_new = new_user_ids & user_ids
        if available_and_new:
            logger.info('Picking new and available user from %s', available_and_new)
            return available_and_new.pop()

        logger.debug('picking user between: %s, team: %s', user_ids, team_id)
        return self.find_least_active_user_id_by_team(user_ids, team_id, start, role_id, cursor, table_name)

    def schedule(self, team, schedules, dbinfo):
        connection, cursor = dbinfo
        events = []
        for schedule in schedules:
            if schedule['auto_populate_threshold'] <= 0:
                self.set_last_epoch(schedule['id'], time.time(), cursor)
                continue
            logger.info('\t\tschedule: %s', str(schedule['id']))
            schedule['timezone'] = team['scheduling_timezone']
            # Calculate events for schedule
            future_events, last_epoch = self.calculate_future_events(schedule, cursor)
            for epoch in future_events:
                # Add (start_time, schedule_id, role_id, roster_id, epoch_events) to events
                events.append((schedule, epoch))
            self.set_last_epoch(schedule['id'], last_epoch, cursor)

        # Create events in the db, associating a user to them
        # Iterate through events in order of (start time, role) to properly assign users
        for schedule, epoch in sorted(events, key=lambda x: (min(ev['start'] for ev in x[1]), x[0]['role_id'])):
            user_id = self.find_next_user_id(schedule, epoch, cursor)
            if not user_id:
                logger.info('Failed to find available user')
                continue
            logger.info('Found user: %s', user_id)
            self.create_events(team['id'], schedule['id'], user_id, epoch, schedule['role_id'], cursor)
        connection.commit()

    def build_preview_response(self, cursor, start__lt, end__ge, team__eq, table_name='temp_event'):
        # get existing events

        cols = all_columns
        query = '''SELECT %s FROM `%s`
                JOIN `user` ON `user`.`id` = `%s`.`user_id`
                JOIN `team` ON `team`.`id` = `%s`.`team_id`
                JOIN `role` ON `role`.`id` = `%s`.`role_id`''' % (cols, table_name, table_name, table_name, table_name)
        where_params = [constraints['start__lt'], constraints['end__ge']]
        where_vals = [start__lt, end__ge]

        # Deal with team subscriptions and team parameters
        team_where = [constraints['team__eq']]
        subs_vals = [team__eq]
        subs_and = ' AND '.join(team_where)
        cursor.execute('''SELECT `subscription_id`, `role_id` FROM `team_subscription`
                        JOIN `team` ON `team_id` = `team`.`id`
                        WHERE %s''' % subs_and, subs_vals)
        if cursor.rowcount != 0:
            # Build where clause based on team params and subscriptions
            subs_and = '(%s OR (%s))' % (subs_and, ' OR '.join(['`team`.`id` = %s AND `role`.`id` = %s' %
                                                                (row['subscription_id'], row['role_id']) for row in cursor]))
        where_params.append(subs_and)
        where_vals += subs_vals

        where_query = ' AND '.join(where_params)
        if where_query:
            query = '%s WHERE %s' % (query, where_query)
        cursor.execute(query, where_vals)
        data = cursor.fetchall()
        return json_dumps(data)

    def populate(self, schedule, start_time, dbinfo, table_name='event'):
        connection, cursor = dbinfo
        start_dt = datetime.fromtimestamp(start_time, utc)
        start_epoch = self.epoch_from_datetime(start_dt)

        # Get schedule info
        role_id = schedule['role_id']
        team_id = schedule['team_id']
        first_event_start = min(ev['start'] for ev in schedule['events'])
        period = self.get_period_len(schedule)
        handoff = start_epoch + timedelta(seconds=first_event_start)
        handoff = timezone(schedule['timezone']).localize(handoff)

        # Start scheduling from the next occurrence of the hand-off time.
        if start_dt > handoff:
            start_epoch += timedelta(weeks=period)
            handoff += timedelta(weeks=period)
        if handoff < utc.localize(datetime.utcnow()):
            cursor.execute("DROP TEMPORARY TABLE IF EXISTS `temp_event`")
            connection.commit()
            raise HTTPBadRequest('Invalid populate/preview request', 'cannot populate/preview starting in the past')

        future_events, last_epoch = self.calculate_future_events(schedule, cursor, start_epoch)
        self.set_last_epoch(schedule['id'], last_epoch, cursor)

        # Delete existing events from the start of the first event
        future_events = [[x for x in evs if x['start'] >= start_time] for evs in future_events]
        future_events = [x for x in future_events if x != []]
        if future_events:
            first_event_start = min(future_events[0], key=lambda x: x['start'])['start']
            query = 'DELETE FROM %s WHERE schedule_id = %%s AND start >= %%s' % table_name
            cursor.execute(query, (schedule['id'], first_event_start))

        # Create events in the db, associating a user to them
        for epoch in future_events:
            user_id = self.find_next_user_id(schedule, epoch, cursor, table_name)
            if not user_id:
                continue
            self.create_events(team_id, schedule['id'], user_id, epoch, role_id, cursor, table_name)
        connection.commit()
