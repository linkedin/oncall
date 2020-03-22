# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPForbidden, HTTP_201

from ...auth import login_required
from .ical_key import get_ical_key, update_ical_key, delete_ical_key, generate_ical_key


@login_required
def on_get(req, resp, user_name):
    """Get the secret key that grants public access to user_name's oncall
    calendar for the logged-in user.

    Current policy only allows the logged-in user to get its own key,
    so user_name parameter must be the same as the logged-in user.

    **Example request:**

    .. sourcecode:: http

        GET /api/v0/ical_key/user/jdoe HTTP/1.1
        Content-Type: text/plain

        ef895425-5f49-11ea-8eee-10e7c6352aff

    """
    challenger = req.context['user']
    if challenger != user_name:
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not allowed to view ical_key of "%s"' % (challenger, user_name)
        )

    key = get_ical_key(challenger, user_name, 'user')
    if key is None:
        raise HTTPNotFound()

    resp.body = key
    resp.set_header('Content-Type', 'text/plain')


@login_required
def on_post(req, resp, user_name):
    """Update or create the secret key that grants public access to
    user_name's oncall calendar for the logged-in user.  Updating the
    secret key will automatically invalidate existing secret keys.  A
    subsequent GET will get the secret key.

    Current policy only allows the logged-in user to get its own key,
    so user_name parameter must be the same as the logged-in user.

    """
    challenger = req.context['user']
    if challenger != user_name:
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not allowed to update ical_key of "%s"' % (challenger, user_name)
        )

    key = generate_ical_key()
    update_ical_key(challenger, user_name, 'user', key)

    resp.status = HTTP_201
    resp.body = key
    resp.set_header('Content-Type', 'text/plain')


@login_required
def on_delete(req, resp, user_name):
    """Delete the secret key that grants public access to user_name's
    oncall calendar for the logged-in user.

    Current policy only allows the logged-in user to get its own key,
    so user_name parameter must be the same as the logged-in user.

    """
    challenger = req.context['user']
    if challenger != user_name:
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not allowed to delete ical_key of "%s"' % (challenger, user_name)
        )

    delete_ical_key(challenger, user_name, 'user')
