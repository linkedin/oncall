from ... import db
from ujson import dumps as json_dumps
from falcon import HTTPError, HTTPBadRequest, HTTP_201
from ...utils import load_json_body
from ...auth import login_required, check_team_auth
import logging

logger = logging.getLogger('oncall-api')


def on_get(req, resp, team):
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''SELECT `subscription`.`name`, `role`.`name` FROM `team`
                      JOIN `team_subscription` ON `team`.`id` = `team_subscription`.`team_id`
                      JOIN `team` `subscription` ON `subscription`.`id` = `team_subscription`.`subscription_id`
                      JOIN `role` ON `role`.`id` = `team_subscription`.`role_id`
                      WHERE `team`.`name` = %s''',
                   team)
    data = [row[0] for row in cursor]
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
            err_msg = 'team "%s" not found' % team
        elif err_msg == 'Column \'role_id\' cannot be null':
            err_msg = 'role "%s" not found' % role_name
        elif err_msg == 'Column \'subscription_id\' cannot be null':
            err_msg = 'team "%s" not found' % sub_name
        logger.exception('Unknown integrity error in team_subscriptions')
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    else:
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201