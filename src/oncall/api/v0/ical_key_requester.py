# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPForbidden
from ujson import dumps as json_dumps

from ...auth import login_required, check_ical_key_admin
from .ical_key import (
    get_ical_key_detail_by_requester,
    invalidate_ical_key_by_requester,
)


@login_required
def on_get(req, resp, requester):
    challenger = req.context['user']
    if not (challenger == requester or check_ical_key_admin(challenger)):
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not allowed to view ical_keys of "%s"' % (challenger, requester),
        )

    results = get_ical_key_detail_by_requester(requester)
    if not results:
        raise HTTPNotFound()

    resp.body = json_dumps(results)
    resp.set_header('Content-Type', 'application/json')


@login_required
def on_delete(req, resp, requester):
    challenger = req.context['user']
    if not (challenger == requester or check_ical_key_admin(challenger)):
        raise HTTPForbidden(
            'Unauthorized',
            'Action not allowed: "%s" is not allowed to delete ical_keys of "%s"' % (challenger, requester),
        )

    invalidate_ical_key_by_requester(requester)
