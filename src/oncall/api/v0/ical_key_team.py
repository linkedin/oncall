# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import uuid

from falcon import HTTPNotFound, HTTP_201

from ...auth import login_required, check_calendar_auth
from .ical_key import get_ical_key, update_ical_key, delete_ical_key


@login_required
def on_get(req, resp, team):
    """Get the secret key that grants public access to team's oncall
    calendar for the logged-in user.

    Current policy only allows access to the team that the logged-in
    user is part of.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/ical_key/team/jteam HTTP/1.1
        Content-Type: text/plain

        ef895425-5f49-11ea-8eee-10e7c6352aff

    """
    challenger = req.context['user']
    check_calendar_auth(team, req)

    key = get_ical_key(challenger, team, 'team')
    if key is None:
        raise HTTPNotFound()

    resp.body = key
    resp.set_header('Content-Type', 'text/plain')


@login_required
def on_post(req, resp, team):
    """Update or create the secret key that grants public access to team's
    oncall calendar for the logged-in user.

    Current policy only allows access to the team that the logged-in
    user is part of.

    """
    challenger = req.context['user']
    check_calendar_auth(team, req)

    update_ical_key(challenger, team, 'team', str(uuid.uuid4()))
    resp.status = HTTP_201


@login_required
def on_delete(req, resp, team):
    """Delete the secret key that grants public access to team's oncall
    calendar for the logged-in user.

    Current policy only allows access to the team that the logged-in
    user is part of.

    """
    challenger = req.context['user']
    check_calendar_auth(team, req)

    delete_ical_key(challenger, team, 'team')
