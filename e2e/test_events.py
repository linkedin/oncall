# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# -*- coding:utf-8 -*-

import time
import requests
from testutils import prefix, api_v0


def test_invalid_events():
    re = requests.get(api_v0('events/undefined'))
    assert re.status_code != 200


@prefix('test_events')
def test_events(event, team, user, role):
    team_name = team.create()
    team_name_2 = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    role_name_2 = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)
    user.add_to_team(user_name_2, team_name_2)
    event.teams.add(team_name)
    event.teams.add(team_name_2)

    start, end = int(time.time()) + 100, int(time.time() + 36000)

    def clean_up():
        re = requests.get(api_v0('events?team=' + team_name))
        for ev in re.json():
            requests.delete(api_v0('events/%d' % ev['id']))

    clean_up()

    # test create event
    re = requests.post(api_v0('events'), json={
        'start': start,
        'end': end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })
    assert re.status_code == 201
    ev_id = re.json()
    assert isinstance(ev_id, int)

    # test end before start
    re = requests.post(api_v0('events'), json={
        'start': end,
        'end': start,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })
    assert re.status_code == 400

    # test create events in past
    re = requests.post(api_v0('events'), json={
        'start': start - 100000,
        'end': start - 5000,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })
    assert re.status_code == 400

    sample_ev = {
        'end': end,
        'start': start,
        'id': ev_id,
        'user': user_name,
        'team': team_name,
        'role': role_name,
        'schedule_id': None,
        'link_id': None,
        'full_name': None,
        'note': None,
    }

    # test get events by team
    re = requests.get(api_v0('events?team__eq=' + team_name))
    assert re.status_code == 200
    events = re.json()
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0] == sample_ev

    # test get events by users
    re = requests.get(api_v0('events?user__eq=' + user_name))
    assert re.status_code == 200
    events = re.json()
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0] == sample_ev

    # test swap events
    re = requests.post(api_v0('events'), json={
        'start': start + 5,
        'end': end + 5,
        'user': user_name_2,
        'team': team_name,
        'role': role_name,
    })
    ev_id2 = re.json()
    re = requests.post(api_v0('events/swap'), json={
        'events': [{'id': ev_id, 'linked': False},
                   {'id': ev_id2, 'linked': False}]
    })
    assert re.status_code == 200
    # verify users swapped
    re = requests.get(api_v0('events?id__eq=%d' % ev_id))
    assert re.status_code == 200
    assert re.json()[0]['user'] == user_name_2

    # test update event
    re = requests.put(api_v0('events/%d' % ev_id), json={
        'start': start - 5, 'end': end - 5, 'user': user_name_2,
        'role': role_name_2
    })
    assert re.status_code == 200
    re = requests.get(api_v0('events/%d' % ev_id))
    assert re.status_code == 200
    new_event = re.json()
    assert new_event['start'] == start - 5
    assert new_event['end'] == end - 5
    assert new_event['user'] == user_name_2
    assert new_event['role'] == role_name_2

    # test invalid event update
    re = requests.put(api_v0('events/%d' % ev_id), json={
        'start': end, 'end': start, 'user': user_name_2,
        'role': role_name_2, 'team': team_name_2
    })
    assert re.status_code == 400

    # test delete event
    re = requests.delete(api_v0('events/%d' % ev_id))
    assert re.status_code == 200
    # verify event is deleted
    re = requests.get(api_v0('events?id__eq=%d' % ev_id))
    assert re.status_code == 200
    assert set(re.json()) == set([])

    clean_up()


@prefix('test_invalid_event_swap')
def test_invalid_event_swap(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)

    start = int(time.time()) + 100

    ev1 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})

    # test swap with invalid event id
    re = requests.post(api_v0('events/swap'), json={
        'events': [{'id': ev1, 'linked': False},
                   {'id': None, 'linked': False}]
    })
    assert re.status_code == 400

    # test swap without event id
    re = requests.post(api_v0('events/swap'), json={
        'events': [{'id': ev1, 'linked': False},
                   {'linked': False}]
    })
    assert re.status_code == 400


@prefix('test_v0_linked_swap')
def test_api_v0_linked_swap(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start = time.time() + 100
    end = start + 50000

    # User 1 linked events
    ev1 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start + 1000,
                        'end': start + 2000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})

    # User 2 linked events
    ev3 = event.create({'start': start + 2000,
                        'end': end - 1000,
                        'user': user_name_2,
                        'team': team_name,
                        'role': role_name})
    ev4 = event.create({'start': end - 1000,
                        'end': end + 1000,
                        'user': user_name_2,
                        'team': team_name,
                        'role': role_name})

    link_id_1 = event.link([ev1, ev2])
    link_id_2 = event.link([ev3, ev4])

    re = requests.post(api_v0('events/swap'), json={
        'events': [{'id': link_id_1, 'linked': True},
                   {'id': link_id_2, 'linked': True}]
    })
    assert re.status_code == 200

    # Check users have swappec
    for ev_id in [ev1, ev2]:
        re = requests.get(api_v0('events?id__eq=%d' % ev_id))
        assert re.status_code == 200
        assert re.json()[0]['user'] == user_name_2

    for ev_id in [ev3, ev4]:
        re = requests.get(api_v0('events?id__eq=%d' % ev_id))
        assert re.status_code == 200
        assert re.json()[0]['user'] == user_name


@prefix('test_v0_link_ev_swap')
def test_api_v0_link_event_swap(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start = time.time() + 100
    end = start + 50000

    # User 1 linked events
    ev1 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start + 1000,
                        'end': start + 2000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})

    # User 2 single event
    ev3 = event.create({'start': start + 2000,
                        'end': end - 1000,
                        'user': user_name_2,
                        'team': team_name,
                        'role': role_name})

    link_id = event.link([ev1, ev2])

    re = requests.post(api_v0('events/swap'), json={
        'events': [{'id': link_id, 'linked': True},
                   {'id': ev3, 'linked': False}]
    })
    assert re.status_code == 200

    # Check users have swapped
    for ev_id in [ev1, ev2]:
        re = requests.get(api_v0('events?id__eq=%d' % ev_id))
        assert re.status_code == 200
        assert re.json()[0]['user'] == user_name_2

    re = requests.get(api_v0('events?id__eq=%d' % ev3))
    assert re.status_code == 200
    assert re.json()[0]['user'] == user_name


@prefix('test_events_link')
def test_events_link(team, user, role):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    role_name_2 = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start, end = int(time.time()), int(time.time() + 36000)

    def clean_up():
        re = requests.get(api_v0('events?team=' + team_name))
        for ev in re.json():
            requests.delete(api_v0('events/%d' % ev['id']))

    clean_up()

    # test create linked events
    re = requests.post(api_v0('events/link'), json=[
        {
            'start': start,
            'end': end,
            'user': user_name,
            'team': team_name,
            'role': role_name,
        },
        {
            'start': start,
            'end': end,
            'user': user_name,
            'team': team_name,
            'role': role_name_2,
        }
    ])
    assert re.status_code == 201
    ev_ids = re.json()['event_ids']
    assert isinstance(ev_ids, list)
    for eid in ev_ids:
        assert isinstance(eid, int)
    evs = [requests.get(api_v0('events/%d' % eid)).json() for eid in ev_ids]
    assert len(evs) == len(ev_ids)
    link_id = evs[0]['link_id']
    for ev in evs:
        assert ev['team'] == team_name
        assert ev['user'] == user_name
        assert ev['start'] == start
        assert ev['end'] == end
        assert ev['link_id'] == link_id

    # Test edit linked events
    re = requests.put(api_v0('events/link/%s' % link_id),
                      json = {'user': user_name_2, 'role': role_name_2, 'note': 'foobar'})
    assert re.status_code == 204
    evs = [requests.get(api_v0('events/%d' % eid)).json() for eid in ev_ids]
    for ev in evs:
        assert ev['team'] == team_name
        assert ev['user'] == user_name_2
        assert ev['start'] == start
        assert ev['end'] == end
        assert ev['link_id'] == link_id
        assert ev['role'] == role_name_2
        assert ev['note'] == 'foobar'

    re = requests.delete(api_v0('events/link/%s' % link_id))
    assert re.status_code == 200
    evs = [requests.get(api_v0('events/%d' % eid)).status_code == 404 for eid in ev_ids]
    assert all(evs)

    clean_up()
