import time
import requests
from testutils import prefix, api_v0


@prefix('test_v0_sub')
def test_api_v0_team_subscription(team, role):
    team_name = team.create()
    team_name_2 = team.create()
    team_name_3 = team.create()
    role_name = role.create()

    re = requests.post(api_v0('teams/%s/subscriptions' % team_name), json={'role': role_name, 'subscription': team_name_2})
    assert re.status_code == 201
    re = requests.post(api_v0('teams/%s/subscriptions' % team_name), json={'role': role_name, 'subscription': team_name_3})
    assert re.status_code == 201

    re = requests.get(api_v0('teams/%s/subscriptions' % team_name))
    assert re.status_code == 200
    data = re.json()
    assert {'role': role_name, 'subscription': team_name_2} in data
    assert {'role': role_name, 'subscription': team_name_3} in data
    assert len(data) == 2

    re = requests.delete(api_v0('teams/%s/subscriptions/%s/%s' % (team_name, team_name_3, role_name)))
    assert re.status_code == 200

    re = requests.get(api_v0('teams/%s/subscriptions' % team_name))
    assert re.status_code == 200
    data = re.json()
    assert {'role': role_name, 'subscription': team_name_2} in data
    assert len(data) == 1


@prefix('test_v0_sub_events')
def test_api_v0_subscription_events(user, role, team, event):
    team_name = team.create()
    team_name_2 = team.create()
    user_name = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name, team_name_2)
    start = int(time.time()) + 1000
    ev1 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start + 1000,
                        'end': start + 2000,
                        'user': user_name,
                        'team': team_name_2,
                        'role': role_name})
    re = requests.post(api_v0('teams/%s/subscriptions' % team_name), json={'role': role_name, 'subscription': team_name_2})
    assert re.status_code == 201
    re = requests.get(api_v0('events?team__eq=%s' % team_name))
    ev_ids = [ev['id'] for ev in re.json()]
    assert ev1 in ev_ids
    assert ev2 in ev_ids

    re = requests.get(api_v0('events?team__eq=%s&include_subscribed=False' % team_name))
    ev_ids = [ev['id'] for ev in re.json()]
    assert ev1 in ev_ids
    assert len(ev_ids) == 1


@prefix('test_v0_sub_oncall')
def test_v0_subscription_oncall(user, role, team, service, event):
    team_name = team.create()
    team_name_2 = team.create()
    service_name = service.create()
    service.associate_team(service_name, team_name)
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name_2)
    re = requests.post(api_v0('teams/%s/subscriptions' % team_name), json={'role': role_name, 'subscription': team_name_2})
    assert re.status_code == 201
    start = int(time.time())

    ev1 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start,
                        'end': start + 1000,
                        'user': user_name_2,
                        'team': team_name_2,
                        'role': role_name})

    re = requests.get(api_v0('services/%s/oncall/%s' % (service_name, role_name)))
    assert re.status_code == 200
    results = re.json()
    users = [ev['user'] for ev in results]
    assert user_name in users
    assert user_name_2 in users
    assert len(results) == 2


@prefix('test_v0_sub_summary')
def test_v0_subscription_summary(user, role, team, event):
    team_name = team.create()
    team_name_2 = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    role_name_2 = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name_2)

    start, end = int(time.time()), int(time.time()+36000)

    event_data_1 = {'start': start,
                    'end': end,
                    'user': user_name,
                    'team': team_name,
                    'role': role_name}
    event_data_2 = {'start': start - 5,
                    'end': end - 5,
                    'user': user_name_2,
                    'team': team_name_2,
                    'role': role_name_2}
    event_data_3 = {'start': start + 50000,
                    'end': end + 50000,
                    'user': user_name,
                    'team': team_name,
                    'role': role_name}
    event_data_4 = {'start': start + 50005,
                    'end': end + 50005,
                    'user': user_name_2,
                    'team': team_name_2,
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

    re = requests.post(api_v0('teams/%s/subscriptions' % team_name), json={'role': role_name_2, 'subscription': team_name_2})
    assert re.status_code == 201

    re = requests.get(api_v0('teams/%s/summary' % team_name))
    assert re.status_code == 200
    results = re.json()
    keys = ['start', 'end', 'role']

    assert all(results['current'][role_name][0][key] == event_data_1[key] for key in keys)
    assert all(results['current'][role_name_2][0][key] == event_data_2[key] for key in keys)
    assert all(results['next'][role_name][0][key] == event_data_3[key] for key in keys)
    assert all(results['next'][role_name_2][0][key] == event_data_4[key] for key in keys)
