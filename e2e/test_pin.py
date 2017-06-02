import requests
from testutils import prefix, api_v0


@prefix('test_v0_pin_team')
def test_v0_pin_team(user, team):
    user_name = user.create()
    team_name = team.create()
    team_name_2 = team.create()

    # Test pinning teams
    re = requests.post(api_v0('users/%s/pinned_teams' % user_name),
                       json={'team': team_name})
    assert re.status_code == 201
    re = requests.post(api_v0('users/%s/pinned_teams' % user_name),
                       json={'team': team_name_2})
    assert re.status_code == 201

    # Test getting pinned teams
    re = requests.get(api_v0('users/%s/pinned_teams' % user_name))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 2
    assert team_name in data
    assert team_name_2 in data

    # Test deleting pinned teams
    re = requests.delete(api_v0('users/%s/pinned_teams/%s' % (user_name, team_name)))
    assert re.status_code == 200

    re = requests.get(api_v0('users/%s/pinned_teams' % user_name))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 1
    assert team_name not in data


@prefix('test_v0_pin_invalid')
def test_api_v0_pin_invalid(user, team):
    user_name = user.create()
    team_name = team.create()

    # Test pinning duplicate team
    re = requests.post(api_v0('users/%s/pinned_teams' % user_name),
                       json={'team': team_name})
    assert re.status_code == 201
    re = requests.post(api_v0('users/%s/pinned_teams' % user_name),
                       json={'team': team_name})
    assert re.status_code == 400

    # Test pinning nonexistent team
    re = requests.post(api_v0('users/%s/pinned_teams' % user_name),
                       json={'team': 'nonexistent-team-foobar'})
    assert re.status_code == 422

    # Test pinning team for nonexistent user
    re = requests.post(api_v0('users/%s/pinned_teams' % 'nonexistent-user-foobar'),
                       json={'team': team_name})
    assert re.status_code == 422

    # Test deleting unpinned team
    re = requests.delete(api_v0('users/%s/pinned_teams/%s' % (user_name, team_name)))
    assert re.status_code == 200
    re = requests.delete(api_v0('users/%s/pinned_teams/%s' % (user_name, team_name)))
    assert re.status_code == 404
