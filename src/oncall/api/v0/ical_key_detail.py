# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPForbidden
from ujson import dumps as json_dumps

from ...auth import login_required, check_ical_key_admin
from .ical_key import get_ical_key_detail, invalidate_ical_key, check_ical_key_requester


@login_required
def on_get(req, resp, key):
    challenger = req.context['user']
    if not (check_ical_key_requester(key, challenger) or check_ical_key_admin(challenger)):
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not an admin of ical_key' % (challenger, ),
        )

    results = get_ical_key_detail(key)
    if not results:
        raise HTTPNotFound()

    resp.body = json_dumps(results)
    resp.set_header('Content-Type', 'application/json')


@login_required
def on_delete(req, resp, key):
    challenger = req.context['user']
    if not (check_ical_key_requester(key, challenger) or check_ical_key_admin(challenger)):
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not an admin of ical_key' % (challenger, ),
        )

    invalidate_ical_key(key)
