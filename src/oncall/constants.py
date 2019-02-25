# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

EMAIL_SUPPORT = 'email'
SMS_SUPPORT = 'sms'
CALL_SUPPORT = 'call'
SLACK_SUPPORT = 'slack'
ROCKET_SUPPORT = 'rocketchat'
TEAMS_SUPPORT = 'teams_messenger'

ONCALL_REMINDER = 'oncall_reminder'
OFFCALL_REMINDER = 'offcall_reminder'
EVENT_CREATED = 'event_created'
EVENT_EDITED = 'event_edited'
EVENT_DELETED = 'event_deleted'
EVENT_SWAPPED = 'event_swapped'
EVENT_SUBSTITUTED = 'event_substituted'

TEAM_CREATED = 'team_created'
TEAM_EDITED = 'team_edited'
TEAM_DELETED = 'team_deleted'
ROSTER_CREATED = 'roster_created'
ROSTER_EDITED = 'roster_edited'
ROSTER_USER_ADDED = 'roster_user_added'
ROSTER_USER_EDITED = 'roster_user_edited'
ROSTER_USER_DELETED = 'roster_user_deleted'
ROSTER_DELETED = 'roster_deleted'
ADMIN_CREATED = 'admin_created'
ADMIN_DELETED = 'admin_deleted'

URGENT = 'urgent'
MEDIUM = 'medium'
CUSTOM = 'custom'

DEFAULT_ROLES = None
DEFAULT_MODES = None
DEFAULT_TIMES = None
GRACE_PERIOD = None

SUPPORTED_TIMEZONES = None


def init(config):
    global DEFAULT_ROLES
    global DEFAULT_MODES
    global DEFAULT_TIMES
    global SUPPORTED_TIMEZONES
    global GRACE_PERIOD
    DEFAULT_ROLES = config['notifications']['default_roles']
    DEFAULT_MODES = config['notifications']['default_modes']
    DEFAULT_TIMES = config['notifications']['default_times']
    SUPPORTED_TIMEZONES = config['supported_timezones']
    GRACE_PERIOD = config.get('grace_period', 86400)
