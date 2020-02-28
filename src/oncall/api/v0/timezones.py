# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ...constants import SUPPORTED_TIMEZONES
from ujson import dumps as json_dumps


def on_get(req, resp):
    resp.body = json_dumps(SUPPORTED_TIMEZONES)
