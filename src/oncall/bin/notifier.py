# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from __future__ import absolute_import

import sys
import yaml
import logging
import time
from importlib import import_module
from pytz import timezone
from ujson import loads as json_loads, dumps as json_dumps
from datetime import datetime
from gevent import queue, spawn, sleep

from oncall import db, metrics, constants
from oncall.messengers import init_messengers, send_message

HOUR = 60 * 60
DAY = HOUR * 24
WEEK = DAY * 7

# logging
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.setLevel(logging.INFO)

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# queue for messages entering the system
send_queue = queue.Queue()

default_timezone = None


def create_reminder(user_id, mode, send_time, context, type_name, cursor):
    context = json_dumps(context)
    cursor.execute('''INSERT INTO `notification_queue`(`user_id`, `send_time`, `mode_id`, `active`, `context`, `type_id`)
                      VALUES (%s,
                              %s,
                              (SELECT `id` FROM `contact_mode` WHERE `name` = %s),
                              1,
                              %s,
                              (SELECT `id` FROM `notification_type` WHERE `name` = %s))''',
                   (user_id, send_time, mode, context, type_name))


def timestamp_to_human_str(timestamp, tz):
    dt = datetime.fromtimestamp(timestamp, timezone(tz))
    return ' '.join([dt.strftime('%Y-%m-%d %H:%M:%S'), tz])


def sec_to_human_str(seconds):
    if seconds % WEEK == 0:
        return '%d weeks' % (seconds / WEEK)
    elif seconds % DAY == 0:
        return '%d days' % (seconds / DAY)
    else:
        return '%d hours' % (seconds / HOUR)


def load_config_file(config_path):
    with open(config_path) as h:
        config = yaml.load(h)

    if 'init_config_hook' in config:
        try:
            module = config['init_config_hook']
            logging.info('Bootstrapping config using %s' % module)
            getattr(import_module(module), module.split('.')[-1])(config)
        except ImportError:
            logger.exception('Failed loading config hook %s' % module)

    return config


def init_notifier(config):
    db.init(config['db'])
    global default_timezone
    default_timezone = config['notifier'].get('default_timezone', 'US/Pacific')
    if config['notifier']['skipsend']:
        global send_message
        send_message = blackhole


def blackhole(msg):
    logger.info('Sent message %s' % msg)
    metrics.stats['message_blackhole_cnt'] += 1


def mark_message_as_sent(msg_info):
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('UPDATE `notification_queue` SET `active` = 0, `sent` = 1 WHERE `id` = %s',
                   msg_info['id'])
    connection.commit()
    connection.close()
    cursor.close()


def mark_message_as_unsent(msg_info):
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('UPDATE `notification_queue` SET `active` = 0, `sent` = 0 WHERE `id` = %s',
                   msg_info['id'])
    connection.commit()
    connection.close()
    cursor.close()


def poll():
    query = '''SELECT `user`.`name` AS `user`, `contact_mode`.`name` AS `mode`, `notification_queue`.`send_time`,
                      `user`.`time_zone`,`notification_type`.`subject`, `notification_queue`.`context`,
                      `notification_type`.`body`, `notification_queue`.`id`
               FROM `notification_queue` JOIN `user` ON `notification_queue`.`user_id` = `user`.`id`
                   JOIN `contact_mode` ON `notification_queue`.`mode_id` = `contact_mode`.`id`
                   JOIN `notification_type` ON `notification_queue`.`type_id` = `notification_type`.`id`
               WHERE `notification_queue`.`active` = 1 AND `notification_queue`.`send_time` <= UNIX_TIMESTAMP()'''
    logger.info('[-] start send task...')

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(query)
    for row in cursor:
        send_queue.put(row)
    cursor.close()
    connection.close()


def worker():
    while 1:
        format_and_send_message()


def format_and_send_message():
    msg_info = send_queue.get()
    msg = {}
    msg['user'] = msg_info['user']
    msg['mode'] = msg_info['mode']
    context = json_loads(msg_info['context'])
    msg['subject'] = msg_info['subject'] % context
    msg['body'] = msg_info['body'] % context
    try:
        send_message(msg)
    except:
        logger.exception('Failed to send message %s', msg)
        mark_message_as_unsent(msg_info)
        metrics.stats['message_fail_cnt'] += 1
    else:
        mark_message_as_sent(msg_info)
        metrics.stats['message_sent_cnt'] += 1


def metrics_sender():
    while True:
        metrics.emit_metrics()
        sleep(60)


def reminder(config):
    interval = config['polling_interval']
    default_timezone = config['default_timezone']

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT `last_window_end` FROM `notifier_state`')
    if cursor.rowcount != 1:
        window_start = int(time.time() - interval)
        logger.warning('Corrupted/missing notifier state; unable to determine last window. Guessing %s',
                       window_start)
    else:
        window_start = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    query = '''
        SELECT `user`.`name`, `user`.`id` AS `user_id`, `time_before`, `contact_mode`.`name` AS `mode`,
               `team`.`name` AS `team`, `event`.`start`, `event`.`id`, `role`.`name` AS `role`, `user`.`time_zone`
        FROM `user` JOIN `notification_setting` ON `notification_setting`.`user_id` = `user`.`id`
                AND `notification_setting`.`type_id` = (SELECT `id` FROM `notification_type`
                                                                  WHERE `name` = %s)
            JOIN `setting_role` ON `notification_setting`.`id` = `setting_role`.`setting_id`
            JOIN `event` ON `event`.`start` >= `time_before` + %s AND `event`.`start` < `time_before` + %s
              AND `event`.`user_id` = `user`.`id`
              AND `event`.`role_id` = `setting_role`.`role_id`
              AND `event`.`team_id` = `notification_setting`.`team_id`
            JOIN `contact_mode` ON `notification_setting`.`mode_id` = `contact_mode`.`id`
            JOIN `team` ON `event`.`team_id` = `team`.`id`
            JOIN `role` ON `event`.`role_id` = `role`.`id`
            LEFT JOIN `event` AS `e` ON `event`.`link_id` = `e`.`link_id` AND `e`.`start` < `event`.`start`
            WHERE `e`.`id` IS NULL
    '''

    while(1):
        logger.info('Reminder polling loop started')
        window_end = int(time.time())

        connection = db.connect()
        cursor = connection.cursor(db.DictCursor)

        cursor.execute(query, (constants.ONCALL_REMINDER, window_start, window_end))
        notifications = cursor.fetchall()

        for row in notifications:
            context = {'team': row['team'],
                       'start_time': timestamp_to_human_str(row['start'],
                                                            row['time_zone'] if row['time_zone'] else default_timezone),
                       'time_before': sec_to_human_str(row['time_before']),
                       'role': row['role']}
            create_reminder(row['user_id'], row['mode'], row['start'] - row['time_before'],
                            context, 'oncall_reminder', cursor)
            logger.info('Created reminder with context %s for %s', context, row['name'])

        cursor.execute('UPDATE `notifier_state` SET `last_window_end` = %s', window_end)
        connection.commit()
        logger.info('Created reminders for window [%s, %s), sleeping for %s s', window_start, window_end, interval)
        window_start = window_end

        cursor.close()
        connection.close()
        sleep(interval)


def main():
    with open(sys.argv[1], 'r') as config_file:
        config = yaml.safe_load(config_file)

    init_notifier(config)
    if 'metrics' in config:
        metrics.init(config, 'oncall-notifier', {'message_blackhole_cnt': 0, 'message_sent_cnt': 0, 'message_fail_cnt': 0})
        spawn(metrics_sender)
    else:
        logger.warning('Not running with metrics')

    init_messengers(config.get('messengers', []))

    worker_tasks = [spawn(worker) for x in xrange(100)]
    spawn(reminder, config['reminder'])

    interval = 60

    logger.info('[*] notifier bootstrapped')
    while True:
        runtime = int(time.time())
        logger.info('--> notifier loop started.')
        poll()

        # check status for all background greenlets and respawn if necessary
        bad_workers = []
        for i, task in enumerate(worker_tasks):
            if not bool(task):
                logger.error("worker task failed, %s", task.exception)
                bad_workers.append(i)
        for i in bad_workers:
            worker_tasks[i] = spawn(worker)

        now = time.time()
        elapsed_time = now - runtime
        nap_time = max(0, interval - elapsed_time)
        logger.info('--> notifier loop finished in %s seconds - sleeping %s seconds',
                    elapsed_time, nap_time)
        sleep(nap_time)


if __name__ == '__main__':
    main()
