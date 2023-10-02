# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# -*- coding:utf-8 -*-

import time
import requests
from testutils import prefix, api_v0
import icalendar
import calendar


@prefix('test_user_ical')
def test_user_ical(event, team, user, role):
    team_name = team.create()
    user_name = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)

    start = int(time.time()) + 100
    end = start + 1000

    ev1 = event.create({'start': start,
                        'end': end,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})

    re = requests.get(api_v0('users/%s/ical' % user_name))
    cal = re.content
    # Parse icalendar, make sure event info is correct
    ical = icalendar.Calendar.from_ical(re.content)
    for component in ical.walk():
        if component.name == 'VEVENT':
            assert user_name in component.get('description')
            assert start == calendar.timegm(component.get('dtstart').dt.timetuple())
            assert end == calendar.timegm(component.get('dtend').dt.timetuple())

@prefix('test_user_ical_exclude_team')
def test_user_ical_exclude_team(event, team, user, role):
    team_name = team.create()
    team_name_2 = team.create()
    user_name = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name, team_name_2)

    start = int(time.time()) + 100
    end = start + 1000

    ev1 = event.create({'start': start,
                        'end': end,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start + 100,
                        'end': end + 100,
                        'user': user_name,
                        'team': team_name_2,
                        'role': role_name})

    re = requests.get(api_v0('users/%s/ical?excludedTeams=%s' % (user_name, team_name_2)))
    cal = re.content
    # Parse icalendar, make sure event info is correct (excluded team's event should not be present)
    ical = icalendar.Calendar.from_ical(re.content)
    num_events = 0
    for component in ical.walk():
        if component.name == 'VEVENT':
            num_events += 1
            assert user_name in component.get('description')
            assert team_name_2 not in component.get('summary')
            assert start == calendar.timegm(component.get('dtstart').dt.timetuple())
            assert end == calendar.timegm(component.get('dtend').dt.timetuple())
    # Make sure that there is only 1 event parsed (excluded team event not included)
    assert num_events == 1


@prefix('test_team_ical')
def test_team_ical(event, team, user, role):
    team_name = team.create()
    user_name = user.create()
    user_name_2 = user.create()
    role_name = role.create()
    user.add_to_team(user_name, team_name)
    user.add_to_team(user_name_2, team_name)

    start = int(time.time()) + 100
    end = start + 1000

    ev1 = event.create({'start': start,
                        'end': end,
                        'user': user_name,
                        'team': team_name,
                        'role': role_name})
    ev2 = event.create({'start': start + 100,
                        'end': end + 100,
                        'user': user_name_2,
                        'team': team_name,
                        'role': role_name})

    re = requests.get(api_v0('teams/%s/ical' % team_name))
    # Parse icalendar, make sure event info is correct
    ical = icalendar.Calendar.from_ical(re.content)
    for component in ical.walk():
        if component.name == 'VEVENT':
            if user_name in component.get('description'):
                assert start == calendar.timegm(component.get('dtstart').dt.timetuple())
                assert end == calendar.timegm(component.get('dtend').dt.timetuple())
                user1 = True
            elif user_name_2 in component.get('description'):
                assert start + 100 == calendar.timegm(component.get('dtstart').dt.timetuple())
                assert end + 100 == calendar.timegm(component.get('dtend').dt.timetuple())
                user2 = True
    # Check that both events appear in the calendar
    assert user1 and user2
