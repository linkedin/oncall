# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# -*- coding:utf-8 -*-

import yaml
from uuid import uuid4
from ujson import loads as json_loads, dumps as json_dumps
from falcon import HTTPBadRequest
from importlib import import_module
from datetime import datetime
from pytz import timezone
from .constants import ONCALL_REMINDER
from . import constants
import re

invalid_char_reg = re.compile(r'[!"#%-,\.\/;->@\[-\^`\{-~]+')
DAY = 86400
WEEK = 604800


# Temporary no-ops to keep legacy API from erroring out
def insert_notification(x, y):
    pass


def update_notification(x, y):
    pass


def read_config(config_path):
    with open(config_path, 'r', encoding='utf8') as config_file:
        return yaml.safe_load(config_file)


def create_notification(context, team_id, role_ids, type_name, users_involved, cursor, **kwargs):
    '''
    :param context: notification context to be formatted into template, dict
    :param team_id: team_id of events
    :param role_ids: iterable of role_ids associated with events
    :param type_name: notification type name (defined in constants.py)
    :param users_involved: iterable of user_ids involved in the action
    :param cursor: DictCursor for db access
    :param kwargs: components of context that require timezone formatting, passed as unix timestamps
    :return: None
    '''
    cursor.execute('''SELECT `user_id`, `mode_id`, `type_id`, `user`.`time_zone` FROM notification_setting
                      JOIN `notification_type` ON `notification_setting`.`type_id` = `notification_type`.`id`
                      JOIN `setting_role` ON `notification_setting`.`id` = `setting_role`.`setting_id`
                      JOIN `user` ON `user_id` = `user`.`id`
                      WHERE team_id = %s AND `setting_role`.`role_id` IN %s AND `notification_type`.`name` = %s
                          AND (user_id IN %s OR only_if_involved = FALSE)
                      GROUP BY `user_id`, `mode_id`
                  ''', (team_id, role_ids, type_name, users_involved))
    notifications = cursor.fetchall()

    for notification in notifications:
        tz = notification['time_zone'] if notification['time_zone'] else 'UTC'
        for var_name, timestamp in kwargs.items():
            context[var_name] = ' '.join([datetime.fromtimestamp(timestamp,
                                                                 timezone(tz)).strftime('%Y-%m-%d %H:%M:%S'),
                                          tz])
        cursor.execute('''INSERT INTO `notification_queue` (`user_id`, `send_time`, `mode_id`, `context`, `type_id`,
                              `active`)
                          VALUES (%s, UNIX_TIMESTAMP(), %s, %s, %s, 1)''',
                       (notification['user_id'], notification['mode_id'], json_dumps(context), notification['type_id']))


def subscribe_notifications(team, user, cursor):
    cursor.execute('SELECT id FROM notification_setting WHERE user_id = (SELECT id FROM user WHERE name = %s) '
                   'AND team_id = (SELECT id FROM team WHERE name = %s)', (user, team))

    if cursor.rowcount == 0:
        for time in constants.DEFAULT_TIMES:
            for mode in constants.DEFAULT_MODES:
                cursor.execute('''INSERT INTO `notification_setting` (`user_id`, `team_id`, `mode_id`,
                                                                      `type_id`, `time_before`)
                                  VALUES ((SELECT id FROM user WHERE name = %s),
                                          (SELECT id FROM team WHERE name = %s),
                                          (SELECT id FROM contact_mode WHERE name = %s LIMIT 1),
                                          (SELECT id FROM notification_type WHERE name = %s),
                                           %s);''',
                               (user, team, mode, ONCALL_REMINDER, time))
            setting_id = cursor.lastrowid
            query_vals = ', '.join(['(%s, (SELECT `id` FROM `role` WHERE `name` = "%s"))' %
                                    (setting_id, role) for role in constants.DEFAULT_ROLES])
            cursor.execute('INSERT INTO `setting_role` VALUES ' + query_vals)


def unsubscribe_notifications(team, user, cursor):
    cursor.execute('DELETE FROM notification_setting WHERE user_id = (SELECT id FROM user WHERE name = %s) '
                   'AND team_id = (SELECT id FROM team WHERE name = %s)', (user, team))


def create_audit(context, team_name, action_name, req, cursor):
    owner_name = req.context.get('user')
    if owner_name is None:
        owner_name = req.context['app']
    cursor.execute('''INSERT INTO audit(`team_name`, `owner_name`, `action_name`, `context`, `timestamp`)
                      VALUES (%s, %s, %s, %s, UNIX_TIMESTAMP())''',
                   (team_name, owner_name, action_name, json_dumps(context)))


def user_in_team(cursor, user_id, team_id):
    cursor.execute('SELECT `id` FROM `user` WHERE `id` = %s '
                   'AND `id` IN (SELECT `user_id` FROM `team_user` WHERE team_id=%s)',
                   (user_id, team_id))
    return cursor.rowcount


def user_in_team_by_name(cursor, user, team):
    cursor.execute('SELECT `id` FROM `user` WHERE `name` = %s '
                   'AND `id` IN (SELECT `user_id` FROM `team_user` '
                   '             WHERE team_id= (SELECT `id` FROM `team` WHERE `name` = %s))',
                   (user, team))
    return cursor.rowcount


def load_json_body(req):
    try:
        return json_loads(req.context['body'])
    except ValueError as e:
        raise HTTPBadRequest('invalid JSON', 'failed to decode json: %s' % str(e))


def import_custom_module(default_root, module):
    if '.' in module:
        module_path = module
        module = module.split('.')[-1]
    else:
        module_path = default_root + '.' + module
    return getattr(import_module(module_path), module)


def gen_link_id():
    return uuid4().hex
