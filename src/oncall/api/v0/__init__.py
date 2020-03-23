# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.


def init(application, config):
    from . import teams, team, team_summary, team_oncall, team_changes
    application.add_route('/api/v0/teams', teams)
    application.add_route('/api/v0/teams/{team}', team)
    application.add_route('/api/v0/teams/{team}/summary', team_summary)
    application.add_route('/api/v0/teams/{team}/oncall', team_oncall)
    application.add_route('/api/v0/teams/{team}/oncall/{role}', team_oncall)
    application.add_route('/api/v0/teams/{team}/changes', team_changes)

    from . import team_admins, team_admin
    application.add_route('/api/v0/teams/{team}/admins', team_admins)
    application.add_route('/api/v0/teams/{team}/admins/{user}', team_admin)

    from . import team_users, team_user
    application.add_route('/api/v0/teams/{team}/users', team_users)
    application.add_route('/api/v0/teams/{team}/users/{user}', team_user)

    from . import rosters, roster, roster_suggest
    application.add_route('/api/v0/teams/{team}/rosters', rosters)
    application.add_route('/api/v0/teams/{team}/rosters/{roster}', roster)
    application.add_route('/api/v0/teams/{team}/rosters/{roster}/{role}/suggest', roster_suggest)

    from . import roster_users, roster_user
    application.add_route('/api/v0/teams/{team}/rosters/{roster}/users', roster_users)
    application.add_route('/api/v0/teams/{team}/rosters/{roster}/users/{user}', roster_user)

    from . import schedules, schedule
    application.add_route('/api/v0/teams/{team}/rosters/{roster}/schedules', schedules)
    application.add_route('/api/v0/schedules/{schedule_id}', schedule)

    from . import populate
    application.add_route('/api/v0/schedules/{schedule_id}/populate', populate)

    from . import preview
    application.add_route('/api/v0/schedules/{schedule_id}/preview', preview)

    from . import services, service, service_oncall
    application.add_route('/api/v0/services', services)
    application.add_route('/api/v0/services/{service}', service)
    application.add_route('/api/v0/services/{service}/oncall', service_oncall)
    application.add_route('/api/v0/services/{service}/oncall/{role}', service_oncall)

    from . import team_services, team_service, service_teams
    application.add_route('/api/v0/teams/{team}/services', team_services)
    application.add_route('/api/v0/teams/{team}/services/{service}', team_service)
    application.add_route('/api/v0/services/{service}/teams', service_teams)

    from . import roles, role
    application.add_route('/api/v0/roles', roles)
    application.add_route('/api/v0/roles/{role}', role)

    from . import events, event, event_swap, event_override, event_link, events_link
    application.add_route('/api/v0/events', events)
    application.add_route('/api/v0/events/{event_id}', event)
    application.add_route('/api/v0/events/swap', event_swap)
    application.add_route('/api/v0/events/override', event_override)
    application.add_route('/api/v0/events/link', events_link)
    application.add_route('/api/v0/events/link/{link_id}', event_link)
    # optional external bonus integration
    if config.get('add_bonus_events_api', None):
        from oncall.api.v0.bonus_events import PaidEvents
        application.add_route('/api/v0/events/bonus', PaidEvents(config))

    from . import users, user, user_teams, user_notifications
    application.add_route('/api/v0/users', users)
    application.add_route('/api/v0/users/{user_name}', user)
    application.add_route('/api/v0/users/{user_name}/teams', user_teams)
    application.add_route('/api/v0/users/{user_name}/notifications', user_notifications)

    from . import user_notification
    application.add_route('/api/v0/notifications/{notification_id}', user_notification)

    from . import notification_types, modes
    application.add_route('/api/v0/notification_types', notification_types)
    application.add_route('/api/v0/modes', modes)

    from . import search
    application.add_route('/api/v0/search', search)

    from . import audit
    application.add_route('/api/v0/audit', audit)

    from . import upcoming_shifts
    application.add_route('/api/v0/users/{user_name}/upcoming', upcoming_shifts)

    from . import user_pinned_teams, user_pinned_team
    application.add_route('/api/v0/users/{user_name}/pinned_teams', user_pinned_teams)
    application.add_route('/api/v0/users/{user_name}/pinned_teams/{team_name}', user_pinned_team)

    from . import timezones
    application.add_route('/api/v0/timezones', timezones)

    from . import team_subscription, team_subscriptions
    application.add_route('/api/v0/teams/{team}/subscriptions', team_subscriptions)
    application.add_route('/api/v0/teams/{team}/subscriptions/{subscription}/{role}', team_subscription)

    from . import user_ical, team_ical
    application.add_route('/api/v0/users/{user_name}/ical', user_ical)
    application.add_route('/api/v0/teams/{team}/ical', team_ical)

    from . import ical_key_user, ical_key_team, ical_key_detail, ical_key_requester
    application.add_route('/api/v0/ical_key/user/{user_name}', ical_key_user)
    application.add_route('/api/v0/ical_key/team/{team}', ical_key_team)
    application.add_route('/api/v0/ical_key/key/{key}', ical_key_detail)
    application.add_route('/api/v0/ical_key/requester/{requester}', ical_key_requester)

    from . import public_ical
    application.add_route('/api/v0/ical/{key}', public_ical)

    # Optional Iris integration
    from . import iris_settings
    application.add_route('/api/v0/iris_settings', iris_settings)
    from ... import iris
    if iris.client and config.get('iris_plan_integration', {}).get('activated'):
        from . import team_iris_escalate
        application.add_route('/api/v0/teams/{team}/iris_escalate', team_iris_escalate)
