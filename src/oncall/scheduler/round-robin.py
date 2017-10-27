from oncall.utils import gen_link_id
import default
import logging

logger = logging.getLogger()

class Scheduler(default.Scheduler):

    def guess_last_scheduled_user(self, schedule, start, roster, cursor):
        cursor.execute('''
                        SELECT MAX(`last_end`), `user_id` FROM
                        (SELECT `user_id`, MAX(`end`) AS `last_end` FROM `event`
                         WHERE `team_id` = %s AND `user_id` IN %s AND `end` <= %s
                         AND `role_id` = %s
                         GROUP BY `user_id`) t
                        GROUP BY `user_id`
                        ''', (schedule['team_id'], roster, start, schedule['role_id']))
        if cursor.rowcount != 0:
            return cursor.fetchone()['user_id']
        else:
            return None

    def find_least_active_available_user_id(self, schedule, future_events, cursor):
        # Ordered by roster priority, break potential ties with user id
        cursor.execute('''SELECT `roster_id`, `user_id`, `roster_priority`
                          FROM roster_user WHERE roster_id = %s AND `in_rotation` = 1
                          ORDER BY roster_priority, user_id''',
                       schedule['roster_id'])
        roster = [row['user_id'] for row in cursor]
        cursor.execute('SELECT last_scheduled_user_id FROM schedule WHERE id = %s', schedule['id'])
        if cursor.rowcount == 0 or roster == []:
            # Schedule doesn't exist, or roster is empty. Bail
            return None
        last_user = cursor.fetchone()['last_scheduled_user_id']
        if last_user not in roster:
            # If this user is no longer in the roster or last_scheduled_user in NULL, try to find
            # the last scheduled user using the calendar
            start = min(e['start'] for e in future_events)
            last_user = self.guess_last_scheduled_user(schedule, start, roster, cursor)
            if last_user is None:
                # If this doesn't work, return the first user in the roster
                return roster[0]
        last_idx = roster.index(last_user)
        return roster[(last_idx + 1) % len(roster)]

    def create_events(self, team_id, schedule_id, user_id, events, role_id, cursor):
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
        cursor.execute('UPDATE `schedule` SET `last_scheduled_user_id` = %s', user_id)
