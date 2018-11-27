from testutils import prefix, api_v0
import requests
import time


@prefix('test_v0_fill_gap_new_user')
def test_api_v0_fill_gap_new_user(user, team, role, roster, event):
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()
    user_name_4 = user.create()
    user_name_5 = user.create()
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    start = int(time.time()) + 100
    user.add_to_roster(user_name, team_name, roster_name)
    user.add_to_roster(user_name_2, team_name, roster_name)
    user.add_to_roster(user_name_3, team_name, roster_name)
    user.add_to_roster(user_name_4, team_name, roster_name)
    user.add_to_roster(user_name_5, team_name, roster_name)
    event.create({'start': start,
                  'end': start + 1000,
                  'user': user_name,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 1000,
                  'end': start + 2000,
                  'user': user_name_2,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 3000,
                  'end': start + 4000,
                  'user': user_name_3,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 4000,
                  'end': start + 5000,
                  'user': user_name_4,
                  'team': team_name,
                  'role': role_name})
    re = requests.get(api_v0('teams/%s/rosters/%s/%s/suggest?start=%s&end=%s' %
                             (team_name, roster_name, role_name, start + 2000, start + 3000)))
    assert re.status_code == 200
    assert re.json()['user'] == user_name_5


@prefix('test_v0_fill_gap')
def test_api_v0_fill_gap(user, team, role, roster, event):
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()
    team_name = team.create()
    role_name = role.create()
    roster_name = roster.create(team_name)
    start = int(time.time()) + 100
    user.add_to_roster(user_name, team_name, roster_name)
    user.add_to_roster(user_name_2, team_name, roster_name)
    user.add_to_roster(user_name_3, team_name, roster_name)
    event.create({'start': start,
                  'end': start + 1000,
                  'user': user_name,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 1000,
                  'end': start + 2000,
                  'user': user_name_2,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 3000,
                  'end': start + 4000,
                  'user': user_name_3,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 4000,
                  'end': start + 5000,
                  'user': user_name,
                  'team': team_name,
                  'role': role_name})
    re = requests.get(api_v0('teams/%s/rosters/%s/%s/suggest?start=%s&end=%s' %
                             (team_name, roster_name, role_name, start + 2000, start + 3000)))
    assert re.status_code == 200
    assert re.json()['user'] == user_name

@prefix('test_v0_fill_gap_skip_busy')
def test_api_v0_fill_gap_skip_busy(user, team, role, roster, event):
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()
    user_name_4 = user.create()
    team_name = team.create()
    role_name = role.create()
    role_name_2 = role.create()
    roster_name = roster.create(team_name)
    start = int(time.time()) + 1000
    user.add_to_roster(user_name, team_name, roster_name)
    user.add_to_roster(user_name_2, team_name, roster_name)
    user.add_to_roster(user_name_3, team_name, roster_name)
    user.add_to_roster(user_name_4, team_name, roster_name)

    # Create events: user_name will be the expected user, with events far from
    # the suggestion time (start + 2000). user_name_4 will be a busy user, who
    # would otherwise be chosen.
    event.create({'start': start,
                  'end': start + 1000,
                  'user': user_name,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 1000,
                  'end': start + 2000,
                  'user': user_name_2,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 3000,
                  'end': start + 4000,
                  'user': user_name_3,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 4000,
                  'end': start + 5000,
                  'user': user_name,
                  'team': team_name,
                  'role': role_name})
    event.create({'start': start + 2500,
                  'end': start + 3000,
                  'user': user_name_4,
                  'team': team_name,
                  'role': role_name_2})
    re = requests.get(api_v0('teams/%s/rosters/%s/%s/suggest?start=%s&end=%s' %
                             (team_name, roster_name, role_name, start + 2000, start + 3000)))
    assert re.status_code == 200
    assert re.json()['user'] == user_name