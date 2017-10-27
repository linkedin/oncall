# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python
# -*- coding:utf-8 -*-

import requests
import ujson
from testutils import prefix, api_v0


@prefix('test_v0_rosters')
def test_api_v0_rosters(team):
    team_name = team.create()
    roster_name = 'test_v0_rosters_roster_0'
    roster_name2 = 'test_v0_rosters_roster_1'

    def clean_up():
        requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
        requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name2)))

    clean_up()

    # test create rosters
    re = requests.post(api_v0('teams/%s/rosters' % team_name),
                       json={'name': roster_name})
    assert re.status_code == 201
    re = requests.post(api_v0('teams/%s/rosters' % team_name),
                       json={'name': roster_name2})
    assert re.status_code == 201

    # test fetch rosters
    re = requests.get(api_v0('teams/%s/rosters' % team_name))
    assert re.status_code == 200
    rosters = re.json()
    assert roster_name in rosters
    assert roster_name2 in rosters

    re = requests.get(api_v0('teams/%s/rosters?name__contains=%s&name__startswith=%s&name__endswith=%s'
                             % (team_name, roster_name, roster_name, roster_name)))
    assert re.status_code == 200
    rosters = re.json()
    assert roster_name in rosters

    roster_id = rosters[roster_name]['id']
    re = requests.get(api_v0('teams/%s/rosters?id=%s' % (team_name, roster_id)))
    assert re.status_code == 200
    rosters = re.json()
    assert roster_name in rosters

    # test fetch single roster
    re = requests.get(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
    assert re.status_code == 200
    roster = re.json()
    assert set(['users', 'schedules']) == set(roster.keys())

    # test rename roster to an existing roster
    re = requests.put(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)),
                      json={'name': roster_name2})
    assert re.status_code == 422
    assert re.json() == {
        'title': 'IntegrityError',
        'description': "roster '%s' already existed for team '%s'" % (roster_name2, team_name),
    }

    # test delete rosters
    re = requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
    assert re.status_code == 200

    re = requests.get(api_v0('teams/%s/rosters' % team_name))
    assert re.status_code == 200
    rosters = re.json()
    assert roster_name not in rosters
    assert roster_name2 in rosters

    re = requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name2)))
    assert re.status_code == 200

    re = requests.get(api_v0('teams/%s/rosters' % team_name))
    assert re.status_code == 200
    rosters = re.json()
    assert len(rosters.keys()) == 0

    clean_up()


@prefix('test_v0_create_invalid_roster')
def test_api_v0_create_invalid_roster(team, roster):
    team_name = team.create()
    roster_name = "v0_create_<inv@lid/_roster"
    re = requests.post(api_v0('teams/%s/rosters' % team_name),
                       json={"name": roster_name})
    assert re.status_code == 400

    roster_name = roster.create(team_name)
    invalid_name = "v0_create_<inv@lid/_roster"
    re = requests.put(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)),
                       json={"name": invalid_name})
    assert re.status_code == 400


@prefix('test_v0_roster_users')
def test_api_v0_rosters_users(team, roster, user):
    team_name = team.create()
    roster_name = roster.create(team_name)
    user_name = user.create()

    def setup():
        requests.post(api_v0('teams/%s/users' % team_name),
                      json={'name': user_name})

    setup()

    # test adding user to a roster
    re = requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                       json={'name': user_name})
    assert re.status_code == 201

    # test fetching users for a roster
    re = requests.get(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([user_name])

    # test deleting user from a roster
    re = requests.delete(
        api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert len(users) == 0


@prefix('test_v0_aut_add_roster')
def test_api_v0_auto_add_rosters_users_to_team(team, user, roster):
    '''
    User should be automatically added to team when added to a roster
    '''
    team_name = team.create()
    roster_name = roster.create(team_name)
    user_name = user.create()

    # make sure user is not in the team
    team = requests.get(api_v0('teams/' + team_name)).json()
    assert user_name not in team['users']

    # add user to roster
    requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                  json={'name': user_name})

    # check to make sure user is also added to the team
    team = requests.get(api_v0('teams/' + team_name)).json()
    assert user_name in team['users']


@prefix('test_v0_rotation')
def test_api_v0_rotation(team, user, roster):
    team_name = team.create()
    user_name = user.create()
    user.add_to_team(user_name, team_name)
    roster_name = roster.create(team_name)
    roster_name_2 = roster.create(team_name)

    # test adding user to a roster out of rotation
    re = requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                       json={'name': user_name, 'in_rotation': False})
    assert re.status_code == 201
    requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name_2)),
                  json={'name': user_name, 'in_rotation': False})

    # test fetching in-rotation users for a roster, verify user is not there
    re = requests.get(api_v0('teams/%s/rosters/%s/users?in_rotation=1' % (team_name, roster_name)))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert len(users) == 0

    # test updating user to put into rotation
    re = requests.put(api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name)),
                      data=ujson.dumps({'in_rotation': True}))
    assert re.status_code == 200

    # verify user is now in rotation
    re = requests.get(api_v0('teams/%s/rosters/%s/users?in_rotation=1' % (team_name, roster_name)))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([user_name])

    # verify other rosters unaffected
    re = requests.get(api_v0('teams/%s/rosters/%s/users?in_rotation=0' % (team_name, roster_name_2)))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([user_name])


@prefix('test_v0_roster_order')
def test_api_v0_roster_order(team, user, roster):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()
    roster_name = roster.create(team_name)
    user.add_to_roster(user_name, team_name, roster_name)
    user.add_to_roster(user_name_2, team_name, roster_name)
    user.add_to_roster(user_name_3, team_name, roster_name)

    re = requests.get(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
    data = re.json()
    users = {u['name']: u for u in data['users']}
    assert users[user_name]['roster_priority'] == 0
    assert users[user_name_2]['roster_priority'] == 1
    assert users[user_name_3]['roster_priority'] == 2

    re = requests.put(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)),
                      json={'roster_order': [user_name_3, user_name_2, user_name]})
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
    data = re.json()
    users = {u['name']: u for u in data['users']}
    assert users[user_name]['roster_priority'] == 2
    assert users[user_name_2]['roster_priority'] == 1
    assert users[user_name_3]['roster_priority'] == 0


# TODO: test invalid user or team

# TODO: test out of rotation

# TODO: test / in roster name
