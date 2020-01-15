# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import datetime
import time
import calendar
import oncall.scheduler.default
from pytz import utc, timezone

MIN = 60
HOUR = 60 * MIN
DAY = 24 * HOUR
WEEK = 7 * DAY

MOCK_SCHEDULE = {'team_id': 1, 'role_id': 2, 'roster_id': 3}


def test_find_new_user_as_least_active_user(mocker):
    scheduler = oncall.scheduler.default.Scheduler()
    mocker.patch('oncall.scheduler.default.Scheduler.find_new_user_in_roster').return_value = {123}
    mocker.patch('oncall.scheduler.default.Scheduler.get_roster_user_ids').return_value = {135, 123}
    mocker.patch('oncall.scheduler.default.Scheduler.get_busy_user_by_event_range')
    mocker.patch('oncall.scheduler.default.Scheduler.find_least_active_user_id_by_team')

    user_id = scheduler.find_next_user_id(MOCK_SCHEDULE, [{'start': 0, 'end': 5}], None)
    assert user_id == 123


def test_calculate_future_events_7_24_shifts(mocker):
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = None
    mock_dt = datetime.datetime(year=2017, month=2, day=7, hour=10)
    mocker.patch('time.time').return_value = time.mktime(mock_dt.timetuple())
    start = DAY + 10 * HOUR + 30 * MIN  # Monday at 10:30 am
    schedule_foo = {
        'timezone': 'US/Pacific',
        'auto_populate_threshold': 21,
        'events': [{
            'start': start,  # 24hr weeklong shift starting Monday at 10:30 am
            'duration': WEEK
        }]
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)
    assert len(future_events) == 4

    mondays = (6, 13, 20, 27)
    for epoch, monday in zip(future_events, mondays):
        assert len(epoch) == 1
        ev = epoch[0]
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Pacific'))
        assert start_dt.timetuple().tm_year == mock_dt.timetuple().tm_year
        assert start_dt.timetuple().tm_mon == mock_dt.timetuple().tm_mon
        assert start_dt.timetuple().tm_mday == monday
        assert start_dt.timetuple().tm_wday == 0   # Monday
        assert start_dt.timetuple().tm_hour == 10  # 10:
        assert start_dt.timetuple().tm_min == 30   # 30 am
        assert start_dt.timetuple().tm_sec == 00
        assert ev['end'] - ev['start'] == WEEK


def test_calculate_future_events_7_12_shifts(mocker):
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = None
    mock_dt = datetime.datetime(year=2016, month=9, day=9, hour=10)
    mocker.patch('time.time').return_value = time.mktime(mock_dt.timetuple())
    start = 3 * DAY + 12 * HOUR  # Wednesday at noon
    events = []
    for i in range(7):
        events.append({'start': start + DAY * i, 'duration': 12 * HOUR})
    schedule_foo = {
        'timezone': 'US/Eastern',
        'auto_populate_threshold': 7,
        'events': events
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)
    assert len(future_events) == 2
    assert len(future_events[0]) == 7
    assert len(future_events[1]) == 7
    days = range(14, 22)
    for ev, day in zip(future_events[1], days):
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Eastern'))
        assert start_dt.timetuple().tm_year == mock_dt.timetuple().tm_year
        assert start_dt.timetuple().tm_mon == mock_dt.timetuple().tm_mon
        assert start_dt.timetuple().tm_mday == day
        assert start_dt.timetuple().tm_hour == 12
        assert start_dt.timetuple().tm_min == 00
        assert start_dt.timetuple().tm_sec == 00


def test_calculate_future_events_14_12_shifts(mocker):
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = None
    mock_dt = datetime.datetime(year=2016, month=9, day=9, hour=10)
    mocker.patch('time.time').return_value = time.mktime(mock_dt.timetuple())
    start = 3 * DAY + 12 * HOUR  # Wednesday at noon
    events = []
    for i in range(14):
        events.append({'start': start + DAY * i, 'duration': 12 * HOUR})
    schedule_foo = {
        'timezone': 'US/Central',
        'auto_populate_threshold': 21,
        'events': events
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)
    assert len(future_events) == 2
    assert len(future_events[1]) == 14
    days = list(range(21, 31)) + list(range(1, 6))
    for ev, day in zip(future_events[1], days):
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Central'))
        assert start_dt.timetuple().tm_year == mock_dt.timetuple().tm_year
        assert start_dt.timetuple().tm_mday == day
        assert start_dt.timetuple().tm_hour == 12
        assert start_dt.timetuple().tm_min == 00
        assert start_dt.timetuple().tm_sec == 00


def test_dst_ambiguous_schedule(mocker):
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = None
    mock_dt = datetime.datetime(year=2016, month=10, day=29, hour=10)
    mocker.patch('time.time').return_value = time.mktime(mock_dt.timetuple())
    start = HOUR + 30 * MIN  # Sunday at 1:30 am
    schedule_foo = {
        'timezone': 'US/Central',
        'auto_populate_threshold': 14,
        'events': [{
            'start': start,  # 24hr weeklong shift starting Sunday at 1:30 am
            'duration': WEEK
        }]
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)

    assert len(future_events) == 3
    dst_events = future_events[1] + future_events[2]
    assert len(dst_events) == 2
    # Make sure that events are consecutive (no gaps)
    assert dst_events[0]['end'] == dst_events[1]['start']


def test_dst_schedule(mocker):
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = None
    mock_dt = datetime.datetime(year=2016, month=10, day=29, hour=10)
    mocker.patch('time.time').return_value = time.mktime(mock_dt.timetuple())
    start = DAY + 11 * HOUR   # Monday at 11:00 am
    schedule_foo = {
        'timezone': 'US/Central',
        'auto_populate_threshold': 14,
        'events': [{
            'start': start,  # 24hr weeklong shift starting Monday at 11:00 am
            'duration': WEEK
        }]
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)

    assert len(future_events) == 3
    dst_events = future_events[1] + future_events[2]
    assert len(dst_events) == 2
    # Make sure that events are consecutive (no gaps)
    assert dst_events[0]['end'] == dst_events[1]['start']
    for ev in dst_events:
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Central'))
        assert start_dt.timetuple().tm_hour == 11


def test_existing_schedule(mocker):
    mock_dt = datetime.datetime(year=2017, month=2, day=5, hour=0, tzinfo=timezone('US/Pacific'))
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = \
        calendar.timegm(mock_dt.astimezone(utc).timetuple())
    mocker.patch('time.time').return_value = time.mktime(datetime.datetime(year=2017, month=2, day=7).timetuple())
    start = DAY + 10 * HOUR + 30 * MIN  # Monday at 10:30 am
    schedule_foo = {
        'timezone': 'US/Pacific',
        'auto_populate_threshold': 21,
        'events': [{
            'start': start,  # 24hr weeklong shift starting Monday at 10:30 am
            'duration': WEEK
        }]
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)
    assert len(future_events) == 3

    mondays = (13, 20, 27)
    for epoch, monday in zip(future_events, mondays):
        assert len(epoch) == 1
        ev = epoch[0]
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Pacific'))
        assert start_dt.timetuple().tm_year == mock_dt.timetuple().tm_year
        assert start_dt.timetuple().tm_mon == mock_dt.timetuple().tm_mon
        assert start_dt.timetuple().tm_mday == monday
        assert start_dt.timetuple().tm_wday == 0   # Monday
        assert start_dt.timetuple().tm_hour == 10  # 10:
        assert start_dt.timetuple().tm_min == 30   # 30 am
        assert start_dt.timetuple().tm_sec == 00
        assert ev['end'] - ev['start'] == WEEK


def test_existing_schedule_change_epoch(mocker):
    mock_dt = datetime.datetime(year=2017, month=2, day=5, hour=0, tzinfo=timezone('US/Eastern'))
    mocker.patch('oncall.scheduler.default.Scheduler.get_schedule_last_epoch').return_value = \
        calendar.timegm(mock_dt.astimezone(utc).timetuple())
    mocker.patch('time.time').return_value = time.mktime(datetime.datetime(year=2017, month=2, day=7).timetuple())
    start = DAY + 10 * HOUR + 30 * MIN  # Monday at 10:30 am
    schedule_foo = {
        'timezone': 'US/Pacific',
        'auto_populate_threshold': 21,
        'events': [{
            'start': start,  # 24hr weeklong shift starting Monday at 10:30 am
            'duration': WEEK
        }]
    }
    scheduler = oncall.scheduler.default.Scheduler()
    future_events, last_epoch = scheduler.calculate_future_events(schedule_foo, None)
    assert len(future_events) == 3

    mondays = (13, 20, 27)
    for epoch, monday in zip(future_events, mondays):
        assert len(epoch) == 1
        ev = epoch[0]
        start_dt = utc.localize(datetime.datetime.utcfromtimestamp(ev['start']))
        start_dt = start_dt.astimezone(timezone('US/Pacific'))
        assert start_dt.timetuple().tm_year == mock_dt.timetuple().tm_year
        assert start_dt.timetuple().tm_mon == mock_dt.timetuple().tm_mon
        assert start_dt.timetuple().tm_mday == monday
        assert start_dt.timetuple().tm_wday == 0   # Monday
        assert start_dt.timetuple().tm_hour == 10  # 10:
        assert start_dt.timetuple().tm_min == 30   # 30 am
        assert start_dt.timetuple().tm_sec == 00
        assert ev['end'] - ev['start'] == WEEK


def test_find_least_active_available_user(mocker):
    mock_user_ids = [123, 456, 789]
    mocker.patch('oncall.scheduler.default.Scheduler.find_new_user_in_roster').return_value = set()
    mocker.patch('oncall.scheduler.default.Scheduler.get_roster_user_ids').return_value = [i for i in mock_user_ids]
    mock_busy_user_by_range = mocker.patch('oncall.scheduler.default.Scheduler.get_busy_user_by_event_range')
    mock_active_user_by_team = mocker.patch('oncall.scheduler.default.Scheduler.find_least_active_user_id_by_team')

    def mock_busy_user_by_range_side_effect(user_ids, team_id, events, cursor, table_name='event'):
        assert user_ids == set(mock_user_ids)
        return [123]

    mock_busy_user_by_range.side_effect = mock_busy_user_by_range_side_effect
    future_events = [{'start': 440, 'end': 570},
                     {'start': 570, 'end': 588},
                     {'start': 600, 'end': 700}]
    scheduler = oncall.scheduler.default.Scheduler()
    scheduler.find_next_user_id(MOCK_SCHEDULE, future_events, None, 'event')

    mock_active_user_by_team.assert_called_with({456, 789}, 1, 440, 2, None, 'event')


def test_find_least_active_available_user_conflicts(mocker):
    mock_user_ids = [123, 456, 789]
    mocker.patch('oncall.scheduler.default.Scheduler.find_new_user_in_roster').return_value = None
    mocker.patch('oncall.scheduler.default.Scheduler.get_roster_user_ids').return_value = [i for i in mock_user_ids]
    mock_busy_user_by_range = mocker.patch('oncall.scheduler.default.Scheduler.get_busy_user_by_event_range')
    mock_active_user_by_team = mocker.patch('oncall.scheduler.default.Scheduler.find_least_active_user_id_by_team')

    def mock_busy_user_by_range_side_effect(user_ids, team_id, events, cursor, table_name='event'):
        assert user_ids == set(mock_user_ids)
        return [123, 456, 789]

    mock_busy_user_by_range.side_effect = mock_busy_user_by_range_side_effect
    future_events = [{'start': 440, 'end': 570}]
    scheduler = oncall.scheduler.default.Scheduler()
    assert scheduler.find_next_user_id(MOCK_SCHEDULE, future_events, None, table_name='event') is None

    mock_active_user_by_team.assert_not_called()
