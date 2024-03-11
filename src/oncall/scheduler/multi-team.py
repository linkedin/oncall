from . import default


class Scheduler(default.Scheduler):
    # same as no-skip-matching
    def create_events(self, team_id, schedule_id, user_id, events, role_id, cursor, table_name='event', skip_match=True):
        super(Scheduler, self).create_events(team_id, schedule_id, user_id, events, role_id, cursor, table_name, skip_match=False)

    def get_busy_user_by_event_range(self, user_ids, team_id, events, cursor, table_name='event'):
        ''' Find which users have overlapping events for the same team in this time range'''
        query_params = [user_ids]
        range_check = []
        for e in events:
            range_check.append('(%s < `end` AND `start` < %s)')
            query_params += [e['start'], e['end']]

        # in multi-team prevent a user being scheduled if they are already scheduled for any role in any team during the same time slot
        query = '''
                SELECT DISTINCT `user_id` FROM `%s`
                WHERE `user_id` in %%s AND (%s)
                ''' % (table_name, ' OR '.join(range_check))

        cursor.execute(query, query_params)
        return [r['user_id'] for r in cursor.fetchall()]