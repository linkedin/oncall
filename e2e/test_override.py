# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import requests
import time
from testutils import prefix,api_v0

start, end = int(time.time()), int(time.time() + 36000)
start = start / 1000 * 1000
end = end / 1000 * 1000


# Helper function to send an override request
def override(start_time, end_time, ev_ids, user):
    re = requests.post(api_v0('events/override'),
                       json={'start': start_time,
                             'end': end_time,
                             'event_ids': ev_ids,
                             'user': user})
    assert re.status_code == 200
    return re


# Test override when events need to be split
@prefix('test_v0_override_split')
def test_api_v0_override_split(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    override_user = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(override_user, team_name)

    ev_id = event.create({'start': start,
                          'end': end,
                          'user': user_name,
                          'team': team_name,
                          'role': role_name})

    re = override(start + 100, end - 100, [ev_id], override_user)
    data = re.json()
    assert len(data) == 3

    re = requests.get(api_v0('events?user=' + user_name))
    events = sorted(re.json(), key=lambda x: x['start'])
    assert len(events) == 2
    assert events[0]['end'] == start + 100
    assert events[1]['start'] == end - 100

    re = requests.get(api_v0('events?user=' + override_user))
    events = re.json()
    assert events[0]['start'] == start + 100
    assert events[0]['end'] == end - 100


# Test override when an event's start needs to be edited
@prefix('test_v0_override_edit_start')
def test_api_v0_override_edit_start(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    override_user = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(override_user, team_name)

    ev_id = event.create({'start': start,
                          'end': end,
                          'user': user_name,
                          'team': team_name,
                          'role': role_name})

    re = override(start, end - 100, [ev_id], override_user)
    data = re.json()
    assert len(data) == 2

    re = requests.get(api_v0('events?user=' + user_name))
    events = re.json()
    assert len(events) == 1
    assert events[0]['end'] == end
    assert events[0]['start'] == end - 100

    re = requests.get(api_v0('events?user=' + override_user))
    events = re.json()
    assert events[0]['start'] == start
    assert events[0]['end'] == end - 100


# Test override when an event's end needs to be edited
@prefix('test_api_v0_override_edit_end')
def test_api_v0_override_edit_end(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    override_user = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(override_user, team_name)

    ev_id = event.create({'start': start,
                          'end': end,
                          'user': user_name,
                          'team': team_name,
                          'role': role_name})

    re = override(start + 100, end, [ev_id], override_user)
    data = re.json()
    assert len(data) == 2

    re = requests.get(api_v0('events?user=' + user_name))
    events = re.json()
    assert len(events) == 1
    assert events[0]['end'] == start + 100
    assert events[0]['start'] == start

    re = requests.get(api_v0('events?user=' + override_user))
    events = re.json()
    assert events[0]['start'] == start + 100
    assert events[0]['end'] == end


# Test override when an event needs to be deleted
@prefix('test_api_v0_override_delete')
def test_api_v0_override_delete(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    override_user = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(override_user, team_name)

    ev_id = event.create({'start': start,
                          'end': end,
                          'user': user_name,
                          'team': team_name,
                          'role': role_name})

    re = override(start - 10, end + 10, [ev_id], override_user)
    assert len(re.json()) == 1

    re = requests.get(api_v0('events?user=' + user_name))
    events = re.json()
    assert len(events) == 0

    re = requests.get(api_v0('events?user=' + override_user))
    events = re.json()
    assert events[0]['start'] == start
    assert events[0]['end'] == end


# Test combination of above cases
@prefix('test_api_v0_override_multiple')
def test_api_v0_override_multiple(team, user, role, event):
    team_name = team.create()
    role_name = role.create()
    user_name = user.create()
    override_user = user.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(override_user, team_name)

    ev1 = event.create({'start': start-1000,
                        'end': start+1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start+1000,
                        'end': start+2000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev3 = event.create({'start': start+2000,
                        'end': end-1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev4 = event.create({'start': end-1000,
                        'end': end+1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})

    re = override(start, end, [ev1, ev2, ev3, ev4], override_user)
    assert len(re.json()) == 3

    re = requests.get(api_v0('events?user=' + user_name))
    events = sorted(re.json(), key=lambda x: x['start'])
    assert len(events) == 2
    assert events[0]['start'] == start - 1000
    assert events[0]['end'] == start
    assert events[1]['start'] == end
    assert events[1]['end'] == end + 1000

    re = requests.get(api_v0('events?user=' + override_user))
    events = re.json()
    assert events[0]['start'] == start
    assert events[0]['end'] == end
