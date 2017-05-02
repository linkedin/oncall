# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

#!/usr/bin/env python
# -*- coding:utf-8 -*-

import requests
from testutils import api_v0

role_name = 'test_role'


def teardown_function():
    requests.delete(api_v0('roles/' + role_name))

def test_roles():
    # test adding role type
    re = requests.post(api_v0('roles'), json={'name': role_name})
    assert re.status_code == 201

    # test getting all roles
    re = requests.get(api_v0('roles'))
    assert re.status_code == 200
    roles = re.json()
    assert isinstance(roles, list)
    assert set([r['name'] for r in roles]) >= set([role_name])

    # test delete
    re = requests.delete(api_v0('roles/'+role_name))
    assert re.status_code == 200
