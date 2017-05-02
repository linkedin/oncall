# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from testutils import prefix, api_v0
import time
import requests


@prefix('test_v0_populate_new')
def test_api_v0_populate_new(user, team, roster, role, schedule):
    user_name = user.create()
    user_name_2 = user.create()
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    schedule_id = schedule.create(team_name,
                                  roster_name,
                                  {'role': role_name,
                                   'events': [{'start': 0, 'duration': 604800}],
                                   'advanced_mode': 0,
                                   'auto_populate_threshold': 14})
    user.add_to_roster(user_name, team_name, roster_name)
    user.add_to_roster(user_name_2, team_name, roster_name)

    def clean_up():
        re = requests.get(api_v0('events?team='+team_name))
        for ev in re.json():
            requests.delete(api_v0('events/%d' % ev['id']))

    clean_up()

    re = requests.post(api_v0('schedules/%s/populate' % schedule_id), json = {'start': time.time()})
    assert re.status_code == 200

    re = requests.get(api_v0('events?team=%s' % team_name))
    assert re.status_code == 200
    events = re.json()
    assert len(events) == 2
    users = set([ev['user'] for ev in events])
    assert user_name in users
    assert user_name_2 in users

    clean_up()


@prefix('test_v0_populate_over')
def test_api_v0_populate_over(user, team, roster, role, schedule):
    user_name = user.create()
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    schedule_id = schedule.create(team_name,
                                  roster_name,
                                  {'role': role_name,
                                   'events': [{'start': 0, 'duration': 604800}],
                                   'advanced_mode': 0,
                                   'auto_populate_threshold': 14})
    user.add_to_roster(user_name, team_name, roster_name)

    def clean_up():
        re = requests.get(api_v0('events?team='+team_name))
        for ev in re.json():
            requests.delete(api_v0('events/%d' % ev['id']))

    clean_up()

    now = time.time()
    re = requests.post(api_v0('schedules/%s/populate' % schedule_id), json = {'start': now})
    assert re.status_code == 200

    re = requests.get(api_v0('events?team=%s' % team_name))
    assert re.status_code == 200
    events = re.json()
    assert len(events) == 2
    # Weekly 12-hour schedule
    new_events = [{'start': 0, 'duration': 43200},
                  {'start': 86400, 'duration': 43200},
                  {'start': 172800, 'duration': 43200},
                  {'start': 259200, 'duration': 43200},
                  {'start': 345600, 'duration': 43200},
                  {'start': 432000, 'duration': 43200},
                  {'start': 518400, 'duration': 43200}]
    re = requests.put(api_v0('schedules/%s' % schedule_id), json={'events': new_events})
    assert re.status_code == 200

    re = requests.post(api_v0('schedules/%s/populate' % schedule_id), json = {'start': now})
    assert re.status_code == 200

    re = requests.get(api_v0('events?team=%s' % team_name))
    assert re.status_code == 200
    events = re.json()

    assert len(events) == 14
    clean_up()


@prefix('test_v0_populate_invalid')
def test_api_v0_populate_invalid(user, team, roster, role, schedule):
    user_name = user.create()
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    schedule_id = schedule.create(team_name,
                                  roster_name,
                                  {'role': role_name,
                                   'events': [{'start': 0, 'duration': 604800}],
                                   'advanced_mode': 0,
                                   'auto_populate_threshold': 14})
    user.add_to_roster(user_name, team_name, roster_name)


    re = requests.post(api_v0('schedules/%s/populate' % schedule_id), json={'start': time.time() - 14 * 24 * 3600})
    assert re.status_code == 400

    # Check this is a no-op
    re = requests.get(api_v0('schedules/%s' % schedule_id))
    assert re.status_code == 200
    schedule_json = re.json()
    re = requests.post(api_v0('schedules/%s/populate' % schedule_id), json={'start': time.time() + 21 * 3600 * 24})
    assert re.status_code == 200
    re = requests.get(api_v0('schedules/%s' % schedule_id))
    assert re.status_code == 200
    re = requests.get(api_v0('schedules/%s' % schedule_id))
    assert re.json() == schedule_json
