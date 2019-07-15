# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python

import pytest
import requests
from uuid import uuid4
from oncall import db
from testutils import api_v0
import os.path
import yaml


@pytest.fixture(scope="session", autouse=True)
def require_db(request):
    # Read config based on pytest root directory. Assumes config lives at oncall/configs/config.yaml
    cfg_path = os.path.join(str(request.config.rootdir), 'configs/config.yaml')
    with open(cfg_path) as f:
        config = yaml.safe_load(f)
    db.init(config['db'])


@pytest.fixture(scope="session", autouse=True)
def require_test_user():
    re = requests.post(api_v0('users'), json={'name': 'test_user'})
    assert re.status_code in [422, 201]


@pytest.fixture(scope="function")
def user(request):

    class UserFactory(object):

        def __init__(self, prefix):
            self.prefix = prefix
            self.created = []

        def create(self):
            name = '_'.join([self.prefix, 'user', str(len(self.created))])
            re = requests.post(api_v0('users'), json={'name': name})
            assert re.status_code in [201, 422]
            self.created.append(name)
            return name

        def add_to_team(self, user, team):
            re = requests.post(api_v0('teams/%s/users' % team), json={'name': user})
            assert re.status_code == 201

        def add_to_roster(self, user, team, roster):
            re = requests.post(api_v0('teams/%s/rosters/%s/users' % (team, roster)),
                               json={'name': user})
            assert re.status_code == 201

        def cleanup(self):
            for user in self.created:
                requests.delete(api_v0('users/' + user))

    factory = UserFactory(request.function.prefix)
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def team(request, user, service):

    class TeamFactory(object):

        def __init__(self, prefix):
            self.prefix = prefix
            self.created = set()
            self.created_ids = set()
            self.connection = db.connect()
            self.cursor = self.connection.cursor()

        def create(self):
            name = '_'.join([self.prefix, 'team', str(len(self.created))])
            re = requests.post(api_v0('teams'), json={'name': name, 'scheduling_timezone': 'utc'})
            assert re.status_code in [201, 422]
            team_id = requests.get(api_v0('teams/%s' % name)).json()['id']
            self.created.add(name)
            self.created_ids.add(team_id)
            return name

        def mark_for_cleaning(self, team_name):
            self.created.add(team_name)

        def cleanup(self):
            for team in self.created:
                requests.delete(api_v0('teams/' + team))
            if self.created_ids:
                self.cursor.execute('DELETE FROM team WHERE id IN %s', (self.created_ids,))
                self.connection.commit()
            self.cursor.close()
            self.connection.close()

    factory = TeamFactory(request.function.prefix)
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def roster(request, team):

    class RosterFactory(object):

        def __init__(self, prefix):
            self.prefix = prefix
            self.created = []

        def init(self, prefix):
            self.prefix = prefix

        def create(self, team_name):
            roster_name = '_'.join([self.prefix, 'roster', str(len(self.created))])
            re = requests.post(api_v0('teams/%s/rosters' % team_name),
                               json={'name': roster_name})
            assert re.status_code in [201, 422]
            self.created.append((roster_name, team_name))
            return roster_name

        def cleanup(self):
            for roster_name, team_name in self.created:
                requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))

    factory = RosterFactory(request.function.prefix)
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def schedule(roster, role):

    class ScheduleFactory(object):
        def __init__(self):
            self.created = []

        def create(self, team_name, roster_name, json):
            re = requests.post(api_v0('teams/%s/rosters/%s/schedules' % (team_name, roster_name)), json=json)
            assert re.status_code == 201
            schedule_id = re.json()['id']
            self.created.append(schedule_id)
            return schedule_id

        def cleanup(self):
            for schedule_id in self.created:
                requests.delete(api_v0('schedules/%d' % schedule_id))

    factory = ScheduleFactory()
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def event(team, role):

    class EventFactory(object):

        def __init__(self, ):
            self.created = []
            self.teams = set()

        def create(self, json):
            re = requests.post(api_v0('events'), json=json)
            assert re.status_code == 201
            ev_id = re.json()
            self.created.append(ev_id)
            self.teams.add(json['team'])
            return ev_id

        def link(self, ids):
            connection = db.connect()
            cursor = connection.cursor()
            link_id = uuid4().hex
            cursor.execute('UPDATE `event` SET `link_id` = %s WHERE `id` IN %s', (link_id, ids))
            connection.commit()
            cursor.close()
            connection.close()
            return link_id

        def cleanup(self):
            for ev in self.created:
                requests.delete(api_v0('events/%d' % ev))
            for t in self.teams:
                re = requests.get(api_v0('events?include_subscribed=false'), params={'team': t})
                for ev in re.json():
                    requests.delete(api_v0('events/%d' % ev['id']))

    factory = EventFactory()
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def role(request, roster):
    class RoleFactory(object):
        def __init__(self, prefix):
            self.prefix = prefix
            self.created = []

        def create(self):
            name = '_'.join([self.prefix, 'role', str(len(self.created))])
            re = requests.post(api_v0('roles'), json={'name': name})
            assert re.status_code in [201, 422]
            self.created.append(name)
            return name

        def cleanup(self):
            for role_name in self.created:
                requests.delete(api_v0('roles/' + role_name))

    factory = RoleFactory(request.function.prefix)
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def service(request):
    class ServiceFactory(object):
        def __init__(self, prefix):
            self.prefix = prefix
            self.created = []
            self.mappings = []

        def create(self):
            name = '_'.join([self.prefix, 'service', str(len(self.created))])
            re = requests.post(api_v0('services'), json={'name': name})
            assert re.status_code in [201, 422]
            self.created.append(name)
            return name

        def associate_team(self, service_name, team_name):
            requests.post(api_v0('teams/%s/services' % team_name),
                          json={'name': service_name})
            self.mappings.append((team_name, service_name))

        def cleanup(self):
            for team_name, service_name in self.mappings:
                requests.delete(api_v0('teams/%s/services/%s' % (team_name, service_name)))
            for service in self.created:
                requests.delete(api_v0('services/' + service))

    factory = ServiceFactory(request.function.prefix)
    yield factory
    factory.cleanup()
