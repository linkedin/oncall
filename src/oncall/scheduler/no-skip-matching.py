from . import default


class Scheduler(default.Scheduler):
    def create_events(self, team_id, schedule_id, user_id, events, role_id, cursor, skip_match=True, table_name='event'):
        super(Scheduler, self).create_events(team_id, schedule_id, user_id, events, role_id, cursor, skip_match=False, table_name='event')