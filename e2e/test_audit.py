# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import requests
import time
from testutils import prefix, api_v0
from oncall.constants import (EVENT_CREATED, EVENT_EDITED, EVENT_SWAPPED, EVENT_DELETED, EVENT_SUBSTITUTED,
                              TEAM_CREATED, TEAM_EDITED, TEAM_DELETED, ROSTER_EDITED, ROSTER_USER_ADDED,
                              ROSTER_CREATED, ROSTER_USER_EDITED, ROSTER_USER_DELETED, ROSTER_DELETED, ADMIN_DELETED,
                              ADMIN_CREATED)

def get_audit_log(start, end):
    re = requests.get(api_v0('audit?start=%s&end=%s&' % (start, end)))
    assert re.status_code == 200
    data = re.json()
    actions = set(audit['action'] for audit in data)
    return actions


@prefix('test_audit')
def test_audit(team, user, role, roster, event):
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    team_name = team.create()

    # test team actions
    start = int(time.time())
    team_name_2 = team.create()
    requests.put(api_v0('teams/'+team_name_2), json={'email': 'foo', 'slack_channel': '#bar', 'slack_channel_notifications': '#bar-alerts'})
    requests.delete(api_v0('teams/%s' % team_name_2))
    end = time.time()
    audit = get_audit_log(start, end)
    assert {TEAM_CREATED, TEAM_DELETED, TEAM_EDITED} <= audit

    # test roster actions
    start = int(time.time())
    roster_name = roster.create(team_name)
    requests.put(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)), json={'name': 'foo'})
    requests.put(api_v0('teams/%s/rosters/foo' % team_name), json={'name': roster_name})
    # roster user actions
    requests.post(api_v0('teams/%s/rosters/%s/users' % (team_name, roster_name)),
                  json={'name': user_name})
    requests.put(api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name)),
                      json={'in_rotation': False})
    requests.delete(api_v0('teams/%s/rosters/%s/users/%s' % (team_name, roster_name, user_name)))
    # delete roster
    requests.delete(api_v0('teams/%s/rosters/%s' % (team_name, roster_name)))
    end = time.time()
    audit = get_audit_log(start, end)
    assert {ROSTER_CREATED, ROSTER_DELETED, ROSTER_USER_ADDED, ROSTER_USER_DELETED,
            ROSTER_EDITED, ROSTER_USER_EDITED} <= audit

    # test event actions
    start = int(time.time())
    ev_start, ev_end = int(time.time()) + 100, int(time.time()) + 36000
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)
    # create event
    ev_id = event.create({
        'start': ev_start,
        'end': ev_end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })
    ev_id_2 = event.create({
        'start': ev_start,
        'end': ev_end,
        'user': user_name,
        'team': team_name,
        'role': role_name,
    })
    # edit event
    re = requests.put(api_v0('events/%d' % ev_id), json={'start': ev_start + 5, 'end': ev_end - 5})
    assert re.status_code == 200
    # swap events
    requests.post(api_v0('events/swap'), json={'events': [{'id': ev_id, 'linked': False},
                                                          {'id': ev_id_2, 'linked': False}]})
    # override event
    requests.post(api_v0('events/override'),
                  json={'start': ev_start,
                        'end': ev_end,
                        'event_ids': [ev_id],
                        'user': user_name_2})
    # delete event
    requests.delete(api_v0('events/%d' % ev_id_2))
    end = time.time()
    audit = get_audit_log(start, end)
    assert {EVENT_DELETED, EVENT_CREATED, EVENT_EDITED, EVENT_SWAPPED, EVENT_SUBSTITUTED} \
           <= audit

    # add/delete admin
    start = int(time.time())
    requests.post(api_v0('teams/%s/admins' % team_name), json={'name': user_name})
    requests.delete(api_v0('teams/%s/admins/%s' % (team_name, user_name)))
    end = time.time()

    audit = get_audit_log(start, end)
    assert {ADMIN_CREATED, ADMIN_DELETED} <= audit
