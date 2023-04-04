from oncall.utils import gen_link_id, create_notification
from ..constants import EVENT_CREATED
from . import default
import logging

logger = logging.getLogger()


class Scheduler(default.Scheduler):

    def guess_last_scheduled_user(self, schedule, start, roster, cursor, table_name='event'):
        query = '''
                        SELECT `last_start`, `user_id` FROM
                        (SELECT `user_id`, MAX(`start`) AS `last_start` FROM `%s`
                         WHERE `team_id` = %%s AND `user_id` IN %%s AND `start` <= %%s
                         AND `role_id` = %%s
                         GROUP BY `user_id`
                         ORDER BY `last_start` DESC) t
                        LIMIT 1
                        ''' % table_name
        cursor.execute(query, (schedule['team_id'], roster, start, schedule['role_id']))
        if cursor.rowcount != 0:
            return cursor.fetchone()['user_id']
        else:
            return None

    def find_next_user_id(self, schedule, future_events, cursor, table_name='event'):
        cursor.execute('''SELECT `user_id` FROM `roster_user`
                           WHERE `roster_id` = %s AND in_rotation = TRUE''',
                       schedule['roster_id'])
        roster_users = {row['user_id'] for row in cursor}
        # Ordered by roster priority, break potential ties with user id
        cursor.execute('''SELECT `user_id`, `priority`
                          FROM schedule_order WHERE schedule_id = %s
                          ORDER BY priority, user_id''',
                       schedule['id'])
        roster = [row['user_id'] for row in cursor if row['user_id'] in roster_users]
        cursor.execute('SELECT last_scheduled_user_id FROM schedule WHERE id = %s', schedule['id'])
        if cursor.rowcount == 0 or roster == []:
            # Schedule doesn't exist, or roster is empty. Bail
            return None
        last_user = cursor.fetchone()['last_scheduled_user_id']
        if last_user not in roster:
            # If this user is no longer in the roster or last_scheduled_user is NULL, try to find
            # the last scheduled user using the calendar
            start = min(e['start'] for e in future_events)
            last_user = self.guess_last_scheduled_user(schedule, start, roster, cursor, table_name)
            if last_user is None:
                # If this doesn't work, return the first user in the roster
                return roster[0]
        last_idx = roster.index(last_user)
        return roster[(last_idx + 1) % len(roster)]

    def create_events(self, team_id, schedule_id, user_id, events, role_id, cursor, table_name='event', skip_match=True):
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
            cursor.execute('SELECT `name` FROM `user` WHERE `id` = %s', user_id)
            name = cursor.fetchone()
            context = {
                'team': team_id,
                'role': role_id,
                'full_name': name
            }
            create_notification(context, team_id,
                                [role_id],
                                EVENT_CREATED,
                                [user_id],
                                cursor,
                                start_time=event['start'])
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
                cursor.execute('SELECT `name` FROM `user` WHERE `id` = %s', user_id)
                name = cursor.fetchone()
                context = {
                    'team': team_id,
                    'role': role_id,
                    'full_name': name
                }
                create_notification(context, team_id,
                                    [role_id],
                                    EVENT_CREATED,
                                    [user_id],
                                    cursor,
                                    start_time=event['start'])
        cursor.execute('UPDATE `schedule` SET `last_scheduled_user_id` = %s WHERE `id` = %s', (user_id, schedule_id))

    def populate(self, schedule, start_time, dbinfo, table_name='event'):
        _, cursor = dbinfo
        # Null last_scheduled_user to force find_next_user to determine that from the calendar
        cursor.execute('UPDATE `schedule` SET `last_scheduled_user_id` = NULL WHERE `id` = %s', schedule['id'])
        super(Scheduler, self).populate(schedule, start_time, dbinfo, table_name=table_name)