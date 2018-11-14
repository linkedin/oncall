# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


def on_get(req, resp, team):
    audit_query = '''SELECT `audit_log`.`description`, `audit_log`.`timestamp`,
                            `audit_log`.`owner_name`, `audit_log`.`action_name`
                     FROM `audit_log` WHERE `team_name` = %s'''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(audit_query, team)
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
