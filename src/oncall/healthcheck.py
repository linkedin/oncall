# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPInternalServerError
from . import db


class HealthCheck(object):

    def __init__(self, config):
        if config.get('debug') or config.get('auth').get('debug'):
            self.dummy_status = 'DEBUG'
        else:
            self.dummy_status = None
            path = config.get('healthcheck_path')
            if not path:
                self.dummy_status = 'BAD'
            else:
                self.path = path

    def on_get(self, req, resp):
        if self.dummy_status:
            status = self.dummy_status
        else:
            try:
                connection = db.connect()
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION();")
                cursor.close()
                connection.close()
            except:
                raise HTTPInternalServerError()
            try:
                with open(self.path) as f:
                    status = f.readline().strip()
            except:
                raise HTTPNotFound()
        resp.content_type = 'text/plain'
        resp.body = status


def init(application, config):
    application.add_route('/healthcheck', HealthCheck(config))
