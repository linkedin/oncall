# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound


def api_not_found(req, resp):
    raise HTTPNotFound


def init(application, config):
    application.add_sink(api_not_found, '/api/')
    from .v0 import init as init_v0
    init_v0(application, config)
