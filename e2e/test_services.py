# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python
# -*- coding:utf-8 -*-

import requests
import time
from testutils import prefix, api_v0


def test_services():
    service_name = 'test_service'

    def clean_up():
        requests.delete(api_v0('services/'+service_name))

    clean_up()
    # test creating services
    re = requests.post(api_v0('services'), json={'name': service_name})
    assert re.status_code == 201

    # test getting all services
    re = requests.get(api_v0('services'))
    assert re.status_code == 200
    services = re.json()
    assert isinstance(services, list)
    assert service_name in set(services)

    # test get one service
    re = requests.get(api_v0('services/'+service_name))
    assert re.status_code == 200
    service = re.json()
    assert isinstance(service, dict)
    assert set(['id', 'name']) == set(service.keys())

    # test delete service
    re = requests.delete(api_v0('services/'+service_name))
    assert re.status_code == 200

    clean_up()


@prefix('test_v0_team_services')
def test_teams_services_mappings(team, service):
    team_name = team.create()
    service_name = service.create()

    # test add associate a service to a team
    re = requests.post(api_v0('teams/%s/services' % team_name),
                       json={'name': service_name})
    assert re.status_code == 201

    # test get all team,service pairs
    re = requests.get(api_v0('team_services'))
    assert re.status_code == 200
    team_services = re.json()
    assert isinstance(team_services, list)
    assert (team_name, service_name) in set((item['team'], item['service']) for item in team_services)

    # test get service list for a team
    re = requests.get(api_v0('teams/%s/services' % team_name))
    assert re.status_code == 200
    services = re.json()
    assert isinstance(services, list)
    assert set(services) == set([service_name])

    # test get team list for a service
    re = requests.get(api_v0('services/%s/teams' % service_name))
    assert re.status_code == 200
    teams = re.json()
    assert isinstance(teams, list)
    assert set(teams) == set([team_name])

    # delete team service mapping
    re = requests.delete(api_v0('teams/%s/services/%s' % (team_name, service_name)))
    assert re.status_code == 200
    # verify delete
    re = requests.get(api_v0('teams/%s/services' % team_name))
    assert re.status_code == 200
    services = re.json()
    assert isinstance(services, list)
    assert len(services) == 0


@prefix('test_v0_service_oncall')
def test_api_v0_services_current_oncall(team, service, user, role, event):
    team_name = team.create()
    service_name = service.create()
    service.associate_team(service_name, team_name)
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    role_name_2 = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)


    start, end = int(time.time()), int(time.time()+36000)
    event_data_1 = {'start': start,
                    'end': end,
                    'user': user_name,
                    'team': team_name,
                    'role': role_name}
    event_data_2 = {'start': start - 5,
                    'end': end - 5,
                    'user': user_name_2,
                    'team': team_name,
                    'role': role_name_2}
    # Create current event
    event.create(event_data_1)
    # Create extra event with different role
    event.create(event_data_2)

    re = requests.get(api_v0('services/%s/oncall/%s' % (service_name, role_name)))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['start'] == start
    assert results[0]['end'] == end

    re = requests.get(api_v0('services/%s/oncall' % service_name))
    assert re.status_code == 200
    results = re.json()
    assert len(results) == 2


@prefix('test_v0_service_override_number')
def test_api_v0_service_override_number(team, user, role, event, service):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    service_name = service.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start, end = int(time.time()), int(time.time()+36000)
    event_data_1 = {'start': start,
                    'end': end,
                    'user': user_name,
                    'team': team_name,
                    'role': 'primary'}
    event.create(event_data_1)

    re = requests.post(api_v0('teams/%s/services' % team_name),
                       json={'name': service_name})
    override_num = '12345'
    re = requests.put(api_v0('teams/'+team_name), json={'override_phone_number': override_num})

    re = requests.get(api_v0('services/%s/oncall/%s' % (service_name, 'primary')))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['start'] == start
    assert results[0]['end'] == end
    assert results[0]['contacts']['call'] == override_num

    re = requests.get(api_v0('services/%s/oncall' % service_name))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['contacts']['call'] == override_num
