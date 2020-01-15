# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import sys
import yaml
import logging
import time
from importlib import import_module
from ujson import loads as json_loads
from gevent import queue, spawn, sleep

from oncall import db, metrics
from oncall.messengers import init_messengers, send_message
from oncall.notifier import reminder, user_validator

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


def load_config_file(config_path):
    with open(config_path) as h:
        config = yaml.safe_load(h)

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
    except Exception:
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


def main():
    with open(sys.argv[1], 'r') as config_file:
        config = yaml.safe_load(config_file)

    init_notifier(config)
    metrics_on = False
    if 'metrics' in config:
        metrics.init(config, 'oncall-notifier', {'message_blackhole_cnt': 0, 'message_sent_cnt': 0, 'message_fail_cnt': 0})
        metrics_worker = spawn(metrics_sender)
        metrics_on = True
    else:
        logger.warning('Not running with metrics')

    init_messengers(config.get('messengers', []))

    worker_tasks = [spawn(worker) for x in range(100)]
    reminder_on = False
    if config['reminder']['activated']:
        reminder_worker = spawn(reminder.reminder, config['reminder'])
        reminder_on = True
    validator_on = False
    if config['user_validator']['activated']:
        validator_worker = spawn(user_validator.user_validator, config['user_validator'])
        validator_on = True

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
        # Check greenlet health for metrics, reminder, and validator tasks
        if metrics_on and not bool(metrics_worker):
            logger.error("metrics worker failed, %s", metrics_worker.exception)
            metrics_worker = spawn(metrics_sender)
        if reminder_on and not bool(reminder_worker):
            logger.error("reminder worker failed, %s", reminder_worker.exception)
            reminder_worker = spawn(reminder.reminder, config['reminder'])
        if validator_on and not bool(validator_worker):
            logger.error("user validator failed, %s", validator_worker.exception)
            validator_worker = spawn(user_validator.user_validator, config['user_validator'])

        now = time.time()
        elapsed_time = now - runtime
        nap_time = max(0, interval - elapsed_time)
        logger.info('--> notifier loop finished in %s seconds - sleeping %s seconds',
                    elapsed_time, nap_time)
        sleep(nap_time)


if __name__ == '__main__':
    main()
