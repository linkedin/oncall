# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python

import requests
import time
from testutils import prefix, api_v0

test_user = 'test_user'


@prefix('test_v0_create_team')
def test_api_v0_create_team(team):
    team_name = "v0_create_team_team"
    requests.delete(api_v0('teams/'+team_name))
    re = requests.post(api_v0('teams'), json={"name": team_name, 'scheduling_timezone': 'utc'})
    assert re.status_code == 201
    # Add to team fixture to ensure cleanup
    team.mark_for_cleaning(team_name)

@prefix('test_v0_create_team_with_space')
def test_api_v0_create_team_with_space(team):
    team_name = "v0_create_team_team"
    team_name_with_space = " v0_create_team_team "
    requests.delete(api_v0('teams/'+team_name))
    re = requests.post(api_v0('teams'), json={"name": team_name_with_space, 'scheduling_timezone': 'utc'})
    teams = requests.get(api_v0('teams')).json()
    assert team_name in teams
    assert team_name_with_space not in teams
    # Add to team fixture to ensure cleanup
    team.mark_for_cleaning(team_name)

@prefix('test_v0_invalid_team')
def test_api_v0_create_invalid_team(team):
    invalid_name = "v0_create_<inv@lid/_team"
    re = requests.post(api_v0('teams'),
                       json={"name": invalid_name, 'scheduling_timezone': 'utc'})
    assert re.status_code == 400

    team_name = team.create()
    re = requests.put(api_v0('teams/%s' % team_name),
                       json={"name": invalid_name})
    assert re.status_code == 400


@prefix('test_v0_get_teams')
def test_api_v0_get_teams(team):
    team_name = team.create()
    re = requests.get(api_v0('teams'))
    assert re.status_code == 200
    teams = re.json()
    assert isinstance(teams, list)
    assert len(teams) >= 1
    assert team_name in teams


@prefix('test_v0_get_team')
def test_api_v0_get_team(team, role, roster, schedule):
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    schedule.create(team_name, roster_name, {'role': role_name,
                                             'events': [{'start': 0, 'duration': 60*60*24*7}],
                                             'advanced_mode': 0})

    # by default, it should return everything
    re = requests.get(api_v0('teams/'+team_name))
    assert re.status_code == 200
    team = re.json()
    assert isinstance(team, dict)
    expected_set = {'users', 'admins', 'services', 'rosters', 'name', 'id', 'slack_channel', 'slack_channel_notifications', 'email',
        'scheduling_timezone', 'iris_plan', 'iris_enabled', 'override_phone_number', 'api_managed_roster'}
    assert expected_set == set(team.keys())

    # it should also support filter by fields
    re = requests.get(api_v0('teams/%s?fields=users&fields=services&fields=admins' % team_name))
    assert re.status_code == 200
    team = re.json()
    assert isinstance(team, dict)
    expected_set = {'users', 'admins', 'services', 'name', 'id', 'slack_channel', 'slack_channel_notifications', 'email',
                    'scheduling_timezone', 'iris_plan', 'iris_enabled', 'override_phone_number', 'api_managed_roster'}
    assert expected_set == set(team.keys())


@prefix('test_v0_delete_team')
def test_api_v0_delete_team(team):
    team_name = team.create()
    requests.post(api_v0('teams'), json={"name": team_name})
    re = requests.delete(api_v0('teams/'+team_name))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/'+team_name))
    assert re.status_code == 404


@prefix('test_v0_update_team')
def test_api_v0_update_team(team):
    team_name = team.create()
    new_team_name = "new-moninfra-update"
    email = 'abc@gmail.com'
    slack = '#slack'
    slack_notifications = '#slack-alerts'

    override_num = '1234'

    # setup DB state
    requests.delete(api_v0('teams/'+new_team_name))
    re = requests.get(api_v0('teams/'+new_team_name))
    assert re.status_code == 404

    re = requests.get(api_v0('teams/'+team_name))
    assert re.status_code == 200
    # edit team name/email/slack
    re = requests.put(api_v0('teams/'+team_name), json={'name': new_team_name,
                                                        'email': email,
                                                        'api_managed_roster': True,
                                                        'slack_channel': slack,
                                                        'slack_channel_notifications': slack_notifications,
                                                        'override_phone_number': override_num})
    assert re.status_code == 200
    team.mark_for_cleaning(new_team_name)
    # verify result
    re = requests.get(api_v0('teams/'+team_name))
    assert re.status_code == 404
    re = requests.get(api_v0('teams/'+new_team_name))
    assert re.status_code == 200
    data = re.json()
    assert data['email'] == email
    assert data['slack_channel'] == slack
    assert data['slack_channel_notifications'] == slack_notifications
    assert data['override_phone_number'] == override_num
    assert data['api_managed_roster'] == 1


@prefix('test_v0_team_admin')
def test_api_v0_team_admin(team, user):

    team_name = team.create()
    re = requests.get(api_v0('teams/%s/admins') % team_name)
    assert re.status_code == 200
    # Make sure the test user was made an admin after making the team
    assert len(re.json()) == 1
    admin_user = user.create()

    # test create admin
    re = requests.post(api_v0('teams/%s/admins' % team_name),
                       json={'name': admin_user})
    assert re.status_code == 201
    # verify result
    re = requests.get(api_v0('teams/%s/admins' % team_name))
    assert re.status_code == 200
    assert admin_user in set(re.json())
    # user should be also added to team automatically
    re = requests.get(api_v0('teams/%s' % team_name))
    assert re.status_code == 200
    assert admin_user in re.json()['users']

    # test delete admin
    re = requests.delete(api_v0('teams/%s/admins/%s' % (team_name, admin_user)))
    # verify result
    re = requests.get(api_v0('teams/%s/admins' % team_name))
    assert re.status_code == 200
    assert admin_user not in set(re.json())


@prefix('test_v0_team_members')
def test_api_v0_team_members(team, user, roster):
    team_name = team.create()
    roster_name = roster.create(team_name)
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()
    none_exist_user = 'team_users_test_random1231_user'

    # make sure we start with an empty team
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert len(users) == 1

    # test add invalid user to the team
    re = requests.post(api_v0('teams/%s/users') % team_name, json={'name': none_exist_user})
    assert re.status_code == 422
    re.json() == {
        'title': 'IntegrityError',
        'description': 'user %s not found' % none_exist_user
    }

    # test add user to team
    re = requests.post(api_v0('teams/%s/users') % team_name, json={'name': user_name})
    assert re.status_code == 201
    # verify team members
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([user_name, test_user])

    # test the user shows up in the team_users endpoint to
    re = requests.get(api_v0('team_users'))
    assert re.status_code == 200
    team_users = re.json()
    assert isinstance(users, list)
    users = set(item['user'] for item in team_users if item['team'] == team_name)
    assert set(users) == set([user_name, test_user])

    # test duplicate user creation
    re = requests.post(api_v0('teams/%s/users') % team_name, json={'name': user_name})
    assert re.status_code == 422
    assert re.json() == {
        'title': 'IntegrityError',
        'description': 'user name "%s" is already in team %s' % (user_name, team_name)
    }

    # test delete user from team
    re = requests.delete(api_v0('teams/%s/users/%s' % (team_name, user_name)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user])

    # test create admin
    re = requests.post(api_v0('teams/%s/admins' % team_name),
                       json={'name': user_name_2})
    assert re.status_code == 201
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user, user_name_2])

    # test add user to roster
    re = requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                       json={'name': user_name_3})
    assert re.status_code == 201
    re = requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                       json={'name': user_name_2})
    assert re.status_code == 201
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user, user_name_2, user_name_3])

    # delete admin/roster-member from team admins, check that they're not removed from team
    re = requests.post(api_v0('teams/%s/admins' % team_name),
                       json={'name': user_name_3})
    assert re.status_code == 201
    re = requests.delete(api_v0('teams/%s/admins/%s' % (team_name, user_name_3)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user, user_name_2, user_name_3])

    # delete from roster too, check they're removed
    re = requests.delete(
        api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name_3)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user, user_name_2])

    # make sure roster but no admin stays in team
    re = requests.delete(api_v0('teams/%s/admins/%s' % (team_name, user_name_2)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user, user_name_2])

    # delete from roster too, check that they're removed
    re = requests.delete(
        api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name_2)))
    assert re.status_code == 200
    re = requests.get(api_v0('teams/%s/users' % team_name))
    assert re.status_code == 200
    users = re.json()
    assert isinstance(users, list)
    assert set(users) == set([test_user])



@prefix('test_v0_summary')
def test_api_v0_team_summary(team, user, role, event):
    team_name = team.create()
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
    event_data_3 = {'start': start + 50000,
                    'end': end + 50000,
                    'user': user_name,
                    'team': team_name,
                    'role': role_name}
    event_data_4 = {'start': start + 50005,
                    'end': end + 50005,
                    'user': user_name_2,
                    'team': team_name,
                    'role': role_name_2}
    event_data_5 = {'start': start + 50001,
                    'end': end + 50001,
                    'user': user_name,
                    'team': team_name,
                    'role': role_name}

    # Create current events
    event.create(event_data_1)
    event.create(event_data_2)
    # Create next events
    event.create(event_data_3)
    event.create(event_data_4)
    # Create extra future event that isn't the next event
    event.create(event_data_5)

    re = requests.get(api_v0('teams/%s/summary' % team_name))
    assert re.status_code == 200
    results = re.json()
    keys = ['start', 'end', 'role', 'user']

    assert all(results['current'][role_name][0][key] == event_data_1[key] for key in keys)
    assert all(results['current'][role_name_2][0][key] == event_data_2[key] for key in keys)
    assert all(results['next'][role_name][0][key] == event_data_3[key] for key in keys)
    assert all(results['next'][role_name_2][0][key] == event_data_4[key] for key in keys)


@prefix('test_v0_summary')
def test_api_v0_non_exist_team_summary(team, user, role, event):
    re = requests.get(api_v0('teams/fobar123bac-n-o-t-found/summary'))
    assert re.status_code == 404


@prefix('test_v0_team_oncall')
def test_api_v0_team_current_oncall(team, user, role, event):
    team_name = team.create()
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
    event.create(event_data_1)
    event.create(event_data_2)

    re = requests.get(api_v0('teams/%s/oncall/%s' % (team_name, role_name)))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['start'] == start
    assert results[0]['end'] == end

    re = requests.get(api_v0('teams/%s/oncall' % team_name))
    assert re.status_code == 200
    results = re.json()
    assert len(results) == 2


@prefix('test_v0_team_override_number')
def test_api_v0_team_override_number(team, user, role, event):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start, end = int(time.time()), int(time.time()+36000)
    event_data_1 = {'start': start,
                    'end': end,
                    'user': user_name,
                    'team': team_name,
                    'role': 'primary'}
    event.create(event_data_1)

    override_num = '12345'
    re = requests.put(api_v0('teams/'+team_name), json={'override_phone_number': override_num})

    re = requests.get(api_v0('teams/%s/oncall/%s' % (team_name, 'primary')))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['start'] == start
    assert results[0]['end'] == end
    assert results[0]['contacts']['call'] == override_num

    re = requests.get(api_v0('teams/%s/oncall' % team_name))
    assert re.status_code == 200
    results = re.json()
    assert results[0]['contacts']['call'] == override_num

    re = requests.get(api_v0('teams/%s/summary' % team_name))
    assert results[0]['contacts']['call'] == override_num
