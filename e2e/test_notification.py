# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import requests
import time
from testutils import prefix, api_v0
from oncall.constants import EVENT_CREATED, EVENT_DELETED, EVENT_SUBSTITUTED, EVENT_SWAPPED, EVENT_EDITED
from oncall import db


def get_notifications(usernames, type_name):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('''SELECT user.name AS user
                      FROM notification_queue JOIN user ON user_id = user.id
                        JOIN notification_type ON notification_queue.type_id = notification_type.id
                      WHERE user_id IN (SELECT id FROM user WHERE name IN %s)
                        AND notification_type.name = %s''',
                   (usernames, type_name))
    ret = cursor.fetchall()
    cursor.close()
    connection.close()
    return ret


@prefix('test_v0_notification')
def test_notification_settings(team, user, role):
    team_name = team.create()
    team_name_2 = team.create()
    user_name = user.create()
    role_name = role.create()
    role_name_2 = role.create()

    def clean_up():
        re = requests.get(api_v0('events?team='+team_name))
        for ev in re.json():
            requests.delete(api_v0('events/%d' % ev['id']))

    clean_up()

    # test get notification settings, make sure there are none
    re = requests.get(api_v0('users/%s/notifications' % user_name))
    assert re.status_code == 200
    assert re.json() == []

    # test adding notification setting
    notification = {'team': team_name, 'roles': [role_name, role_name_2], 'mode': 'email', 'type': EVENT_CREATED,
                    'only_if_involved': True}
    re = requests.post(api_v0('users/%s/notifications' % user_name), json=notification)
    assert re.status_code == 201
    setting_id = re.json()['id']

    # check that setting values are correct
    re = requests.get(api_v0('users/%s/notifications' % user_name))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 1
    assert all([notification[key] == data[0][key] for key in notification])

    # test editing setting
    new_setting = {'team': team_name_2, 'roles': [role_name_2], 'mode': 'sms', 'type': EVENT_DELETED,
                   'only_if_involved': False}
    re = requests.put(api_v0('notifications/%s' % setting_id), json=new_setting)
    assert re.status_code == 200

    # check that setting now has new values
    re = requests.get(api_v0('users/%s/notifications' % user_name))
    assert re.status_code == 200
    data = re.json()
    assert len(data) == 1
    assert all([new_setting[key] == data[0][key] for key in new_setting])

    # test deleting setting
    re = requests.delete(api_v0('notifications/%s' % setting_id))
    assert re.status_code == 200

    # make sure it was deleted
    re = requests.get(api_v0('users/%s/notifications' % user_name))
    assert re.status_code == 200
    assert re.json() == []


@prefix('v0_test_notify_on_ev_actions')
def test_notify_on_ev_actions(user, team, role, event):
    user_name = user.create()
    user_name_2 = user.create()
    user_name_3 = user.create()

    team_name = team.create()
    team_name_2 = team.create()
    role_name = role.create()
    role_name_2 = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)


    start, end = int(time.time() + 100), int(time.time() + 36000)

    # For each type, create settings
    for type_name in (EVENT_CREATED, EVENT_EDITED, EVENT_DELETED):
        notification = {'team': team_name, 'roles': [role_name], 'mode': 'email', 'type': type_name,
                        'only_if_involved': True}
        re = requests.post(api_v0('users/%s/notifications' % user_name), json=notification)
        assert re.status_code == 201

        # create identical setting for user_2
        re = requests.post(api_v0('users/%s/notifications' % user_name_2), json=notification)
        assert re.status_code == 201

        # make setting where only_if_involved is False
        new_notification = notification.copy()
        new_notification['only_if_involved'] = False
        re = requests.post(api_v0('users/%s/notifications' % user_name_3), json=new_notification)
        assert re.status_code == 201

        # make settings for user_2 with different team/role
        new_notification = notification.copy()
        new_notification['team'] = team_name_2
        re = requests.post(api_v0('users/%s/notifications' % user_name_2), json=new_notification)
        assert re.status_code == 201

        new_notification = notification.copy()
        new_notification['roles'] = [role_name_2]
        re = requests.post(api_v0('users/%s/notifications' % user_name_2), json=new_notification)
        assert re.status_code == 201

    # create event
    ev_id = event.create({
        'start': start,
        'end': end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })

    # Check that notifications were created for users 1 and 3 (not 2)
    notifications = get_notifications([user_name, user_name_2, user_name_3], EVENT_CREATED)
    assert len(notifications) == 2
    assert {n['user'] for n in notifications} == {user_name, user_name_3}

    # Edit event
    re = requests.put(api_v0('events/%d' % ev_id), json={'start': start + 5, 'end': end - 5, 'user': user_name_2,
                                                         'role': role_name_2})
    assert re.status_code == 200
    # Check that each user got a notification
    notifications = get_notifications([user_name, user_name_2, user_name_3], EVENT_EDITED)
    assert len(notifications) == 3
    assert {n['user'] for n in notifications} == {user_name, user_name_2, user_name_3}

    # Delete event
    re = requests.delete(api_v0('events/%d' % ev_id))
    assert re.status_code == 200
    # Check that user 2 got a notification
    notifications = get_notifications([user_name, user_name_2, user_name_3], EVENT_DELETED)
    assert len(notifications) == 1
    assert {n['user'] for n in notifications} == {user_name_2}


@prefix('v0_test_notify_on_swap')
def test_notify_on_swap(user, role, team, event):
    user_name = user.create()
    user_name_2 = user.create()
    team_name = team.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start, end = int(time.time() + 100), int(time.time() + 36000)

    ev_id = event.create({
        'start': start,
        'end': end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })

    ev_id_2 = event.create({
        'start': start + 100,
        'end': end + 100,
        'user': user_name_2,
        'team': team_name,
        'role': role_name,
    })

    # set up notification settings
    notification = {'team': team_name, 'roles': [role_name], 'mode': 'email', 'type': EVENT_SWAPPED,
                    'only_if_involved': True}
    re = requests.post(api_v0('users/%s/notifications' % user_name), json=notification)
    assert re.status_code == 201
    re = requests.post(api_v0('users/%s/notifications' % user_name_2), json=notification)
    assert re.status_code == 201

    # Swap these events
    re = requests.post(api_v0('events/swap'), json={'events': [{'id': ev_id, 'linked': False},
                                                               {'id': ev_id_2, 'linked': False}]})
    assert re.status_code == 200

    notifications = get_notifications([user_name, user_name_2], EVENT_SWAPPED)
    assert len(notifications) == 2
    assert {n['user'] for n in notifications} == {user_name, user_name_2}


@prefix('v0_test_notify_on_override')
def test_notify_on_override(user, role, team, event):
    user_name = user.create()
    user_name_2 = user.create()
    team_name = team.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start, end = int(time.time() + 100), int(time.time() + 36000)

    ev_id = event.create({
        'start': start,
        'end': end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })

    # set up notification settings
    notification = {'team': team_name, 'roles': [role_name], 'mode': 'email', 'type': EVENT_SUBSTITUTED,
                    'only_if_involved': True}
    re = requests.post(api_v0('users/%s/notifications' % user_name), json=notification)
    assert re.status_code == 201
    re = requests.post(api_v0('users/%s/notifications' % user_name_2), json=notification)
    assert re.status_code == 201

    re = requests.post(api_v0('events/override'),
                       json={'start': start + 200,
                             'end': end - 200,
                             'event_ids': [ev_id],
                             'user': user_name_2})
    assert re.status_code == 200

    notifications = get_notifications([user_name, user_name_2], EVENT_SUBSTITUTED)
    assert len(notifications) == 2
    assert {n['user'] for n in notifications} == {user_name, user_name_2}
