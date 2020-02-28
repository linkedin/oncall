# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps as json_dumps
from falcon import HTTPError, HTTPBadRequest, HTTP_201
from ...utils import load_json_body
from ...auth import login_required, check_team_auth
import logging

logger = logging.getLogger('oncall-api')


def on_get(req, resp, team):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('''SELECT `subscription`.`name` AS `subscription`, `role`.`name` AS `role` FROM `team`
                      JOIN `team_subscription` ON `team`.`id` = `team_subscription`.`team_id`
                      JOIN `team` `subscription` ON `subscription`.`id` = `team_subscription`.`subscription_id`
                      JOIN `role` ON `role`.`id` = `team_subscription`.`role_id`
                      WHERE `team`.`name` = %s''',
                   team)
    data = [row for row in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp, team):
    data = load_json_body(req)
    check_team_auth(team, req)
    sub_name = data.get('subscription')
    role_name = data.get('role')
    if not sub_name or not role_name:
        raise HTTPBadRequest('Invalid subscription', 'Missing subscription name or role name')
    if sub_name == team:
        raise HTTPBadRequest('Invalid subscription', 'Subscription team must be different from subscribing team')
    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('''INSERT INTO `team_subscription` (`team_id`, `subscription_id`, `role_id`) VALUES
                          ((SELECT `id` FROM `team` WHERE `name` = %s),
                           (SELECT `id` FROM `team` WHERE `name` = %s),
                           (SELECT `id` FROM `role` WHERE `name` = %s))''',
                       (team, sub_name, role_name))
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == 'Column \'team_id\' cannot be null':
            err_msg = 'Team "%s" not found' % team
        elif err_msg == 'Column \'role_id\' cannot be null':
            err_msg = 'Role "%s" not found' % role_name
        elif err_msg == 'Column \'subscription_id\' cannot be null':
            err_msg = 'Team "%s" not found' % sub_name
        elif err_msg.startswith('Duplicate entry'):
            err_msg = 'Subscription already exists'
        else:
            logger.exception('Unknown integrity error in team_subscriptions')
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
