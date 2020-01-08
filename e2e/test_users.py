# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python
# -*- coding:utf-8 -*-

import requests
import json
from testutils import prefix, api_v0


def test_api_v0_users():
    user_name = 'test_v0_users_user'

    def clean_up():
        requests.delete(api_v0('users/'+user_name))

    clean_up()

    # test adding user
    re = requests.post(api_v0('users'), json={'name': user_name})
    assert re.status_code == 201

    re = requests.get(api_v0('users/'+user_name))
    assert re.status_code == 200
    response = json.loads(re.text)
    assert 'contacts' in response
    assert response['full_name'] != 'Juan Doş'

    # test updating user
    re = requests.put(api_v0('users/'+user_name), json={'full_name': 'Juan Doş', 'time_zone': 'PDT'})
    assert re.status_code == 204

    # test updating user contacts
    re = requests.put(api_v0('users/'+user_name), json={'full_name': 'Juan Doş', 'contacts': {'call': '+1 333-333-3339'}})
    assert re.status_code == 204

    # make sure update has gone through, test get
    re = requests.get(api_v0('users/'+user_name))
    assert re.status_code == 200
    response = re.json()
    assert response['full_name'] == 'Juan Doş'

    user_id = response['id']
    re = requests.get(api_v0('users?id=%s' % user_id))
    assert re.status_code == 200
    response = re.json()
    assert response[0]['full_name'] == 'Juan Doş'

    re = requests.get(api_v0('users'), params={'name': user_name, 'fields': ['full_name', 'time_zone', 'contacts']})
    assert re.status_code == 200
    response = json.loads(re.text)
    assert response[0]['full_name'] == 'Juan Doş'
    assert response[0]['time_zone'] == 'PDT'
    assert response[0]['contacts']['call'] == '+1 333-333-3339'

    clean_up()


@prefix('test_v0_user_teams')
def test_api_v0_user_teams(team, user):
    team_name = team.create()
    user_name = user.create()

    # should get an empty team list
    re = requests.get(api_v0('users/%s/teams' % user_name))
    assert re.status_code == 200
    assert re.json() == []

    # should not get an empty team list
    re = requests.post(api_v0('teams/%s/users' % team_name), json={'name': user_name})
    assert re.status_code == 201
    re = requests.get(api_v0('users/%s/teams' % user_name))
    assert re.status_code == 200
    assert team_name in re.json()

    # should get 404 on invalid user
    re = requests.get(api_v0('users/invalid_user_foobar-123/teams'))
    assert re.status_code == 404
