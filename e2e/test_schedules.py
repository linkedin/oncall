# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python
# -*- coding:utf-8 -*-

import urllib.parse
import requests
from testutils import prefix, api_v0

HOUR = 60 * 60
DAY = HOUR * 24


@prefix('test_v0_schedules')
def test_api_v0_schedules(team, roster, role):
    tuesday9am = 2 * DAY + 9 * HOUR
    tuesday9pm = tuesday9am + 12 * HOUR
    wednesday9am = tuesday9pm + 12 * HOUR
    wednesday9pm = wednesday9am + 12 * HOUR

    team_name = team.create()
    team_name_2 = team.create()
    roster_name = roster.create(team_name)
    roster_name_2 = roster.create(team_name_2)
    role_name = role.create()
    role_name_2 = role.create()

    # test create schedule
    events = [{'start': tuesday9am, 'duration': 12 * HOUR},
              {'start': tuesday9pm, 'duration': 12 * HOUR},
              {'start': wednesday9am, 'duration': 12 * HOUR},
              {'start': wednesday9pm, 'duration': 12 * HOUR}]
    re = requests.post(api_v0('teams/%s/rosters/%s/schedules' % (team_name, roster_name)),
                       json={
                           'role': role_name,
                           'events': events,
                           'advanced_mode': 1
                       })
    assert re.status_code == 201
    schedule_id = str(re.json()['id'])

    # verify schedule created properly
    re = requests.get(api_v0('teams/%s/rosters/%s/schedules' % (team_name, roster_name)))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 1
    schedule = data[0]
    assert schedule['role'] == role_name
    # check consecutive events have been merged
    assert len(schedule['events']) == 1
    assert schedule['events'][0]['start'] == tuesday9am
    assert schedule['events'][0]['duration'] == 48 * HOUR
    assert schedule['advanced_mode'] == 1

    # test 'schedule' endpoint
    re = requests.get(api_v0('schedules/%s' % (schedule_id)))
    assert re.status_code == 200
    assert re.json() == data[0]

    updated_events = [{'start': 0, 'duration': 100}, {'start': 150, 'duration': 200}]
    # verify schedule updates properly
    re = requests.put(api_v0('schedules/' + schedule_id),
                      json={'role': role_name_2,
                            'team': team_name_2,
                            'roster': roster_name_2,
                            'auto_populate_threshold': 28,
                            'events': updated_events,
                            'advanced_mode': 1})
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/rosters/%s/schedules' % (team_name_2, roster_name_2)))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 1
    schedule = data[0]
    assert schedule['roster'] == roster_name_2
    assert schedule['role'] == role_name_2
    assert schedule['auto_populate_threshold'] == 28
    assert schedule['events'] == updated_events
    assert schedule['advanced_mode'] == 1

    re = requests.put(api_v0('schedules/' + schedule_id), json={'team': team_name, 'roster': roster_name})
    assert re.status_code == 200

    # test delete schedule
    re = requests.delete(api_v0('schedules/' + schedule_id))
    assert re.status_code == 200

    # verify schedule was deleted
    re = requests.get(api_v0('teams/%s/rosters/%s/schedules' % (team_name_2, roster_name_2)))
    assert re.status_code == 200
    data = re.json()
    assert data == []


@prefix('test_v0_advanced_schedule')
def test_api_v0_advanced_schedule(team, roster, role, schedule):
    team_name = team.create()
    roster_name = roster.create(team_name)
    role_name = role.create()
    schedule_id = schedule.create(team_name,
                                  roster_name,
                                  {'role': role_name,
                                   'events': [{'start': 0, 'duration': 100},
                                              {'start': 200, 'duration': 300}],
                                   'advanced_mode': 1})

    # check invalid schedule updates
    re = requests.put(api_v0('schedules/%d' % schedule_id), json={'events': [{'start': 0, 'duration': 100},
                                                                             {'start': 150, 'duration': 300}],
                                                                  'advanced_mode': 0})
    assert re.status_code == 400
    re = requests.put(api_v0('schedules/%d' % schedule_id), json={'advanced_mode': 0})
    assert re.status_code == 400


@prefix('test_v0_invalid_schedule_event')
def test_api_v0_invalid_schedule_event(team, roster, role, schedule):
    team_name = team.create()
    roster_name = roster.create(team_name)
    role_name = role.create()
    api_url = api_v0('teams/%s/rosters/%s/schedules' % (team_name, roster_name))
    re = requests.post(api_url, json={
        'role': role_name,
        'events': [{'duration': 100},
                   {'start': 150, 'duration': 300}],
        'advanced_mode': 1
    })
    assert re.status_code == 400

    re = requests.post(api_url, json={
        'role': role_name,
        'events': [{'start': 150}],
        'advanced_mode': 1
    })
    assert re.status_code == 400

    re = requests.post(api_url, json={
        'role': role_name,
        'events': [{'start': 150, 'duration': 300}],
        'advanced_mode': 0
    })
    assert re.status_code == 400

    re = requests.post(api_url, json={
        'role': role_name,
        'events': 7 * [{'start': 150, 'duration': 300}],
        'advanced_mode': 0
    })
    assert re.status_code == 400


@prefix('test_v0_schedules_spaces')
def test_api_v0_schedules_with_spaces_in_roster_name(team):
    team_name = 'test_v0 spaces team foo'
    roster_name = 'test_v0 spaces roster foo'

    re = requests.post(api_v0('teams'), json={'name': team_name, 'scheduling_timezone': 'UTC'})
    assert re.status_code == 201
    team.mark_for_cleaning(team_name)
    re = requests.post(api_v0('teams/%s/rosters' % team_name),
                       json={'name': roster_name})
    assert re.status_code == 201

    re = requests.get(api_v0('teams/%s/rosters/%s/schedules' %
                             (team_name, urllib.parse.quote(roster_name, safe=''))))
    assert re.status_code == 200
