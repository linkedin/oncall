# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPBadRequest, HTTP_201

from ...auth import login_required
from .ical_key import (
    get_ical_key,
    update_ical_key,
    delete_ical_key,
    generate_ical_key,
    check_ical_team,
)


@login_required
def on_get(req, resp, team):
    """Get the secret key that grants public access to team's oncall
    calendar for the logged-in user.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/ical_key/team/jteam HTTP/1.1
        Content-Type: text/plain

        ef895425-5f49-11ea-8eee-10e7c6352aff

    """
    challenger = req.context['user']

    key = get_ical_key(challenger, team, 'team')
    if key is None:
        raise HTTPNotFound()

    resp.body = key
    resp.set_header('Content-Type', 'text/plain')


@login_required
def on_post(req, resp, team):
    """Update or create the secret key that grants public access to team's
    oncall calendar for the logged-in user.

    """
    challenger = req.context['user']
    if not check_ical_team(team, challenger):
        raise HTTPBadRequest(
            'Invalid team name',
            'Team "%s" does not exist or is inactive' % team,
        )

    key = generate_ical_key()
    update_ical_key(challenger, team, 'team', key)

    resp.status = HTTP_201
    resp.body = key
    resp.set_header('Content-Type', 'text/plain')


@login_required
def on_delete(req, resp, team):
    """Delete the secret key that grants public access to team's oncall
    calendar for the logged-in user.

    """
    challenger = req.context['user']

    delete_ical_key(challenger, team, 'team')
