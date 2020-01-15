#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
from gevent import sleep
import logging

from phonenumbers import format_number, parse, PhoneNumberFormat
from slackclient import SlackClient
from oncall import db

logger = logging.getLogger(__name__)


def normalize_phone_number(num):
    return format_number(parse(num.decode('utf-8'), 'US'), PhoneNumberFormat.INTERNATIONAL)


def fetch_oncall_usernames(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT `name` FROM `user`')
    users = [row[0] for row in cursor]
    cursor.close()
    return users


def insert_users(connection, slack_users, users_to_insert, mode_ids):
    cursor = connection.cursor()
    for username in users_to_insert:
        user_info = slack_users[username]
        cursor.execute(
            '''INSERT INTO `user` (`name`, `full_name`, `photo_url`)
               VALUES (%s, %s, %s)''',
            (username, user_info['full_name'], user_info['photo_url']))
        connection.commit()
        user_id = cursor.lastrowid
        contact_rows = [(user_id, mode_ids['slack'], username)]
        if 'email' in user_info:
            contact_rows.append((user_id, mode_ids['email'], user_info['email']))
        if 'phone' in user_info:
            contact_rows.append((user_id, mode_ids['call'], user_info['phone']))
            contact_rows.append((user_id, mode_ids['sms'], user_info['phone']))
        if contact_rows:
            cursor.executemany(
                '''INSERT INTO `user_contact` (`user_id`, `mode_id`, `destination`)
                   VALUES (%s, %s, %s)''',
                contact_rows)
            connection.commit()
    cursor.close()
    logger.info('Inserted %s users', len(users_to_insert))


def delete_users(connection, users_to_delete):
    cursor = connection.cursor()
    cursor.execute('UPDATE `user` SET `active` = 0 WHERE `name` IN %s', users_to_delete)
    connection.commit()
    cursor.close()
    logger.info('Marked %s users as inactive', len(users_to_delete))


def sync_action(slack_client):
    re = slack_client.api_call("users.list")
    if not re.get('ok'):
        logger.error('Failed to fetch user list from slack')
        return

    slack_members = re['members']
    slack_users = {}

    for m in slack_members:
        if m['name'] == 'slackbot' or m['deleted']:
            continue
        user_profile = m['profile']
        slack_users[m['name']] = {
            'name': m['name'],
            'full_name': user_profile['real_name'],
            'photo_url': user_profile['image_512'],
            'email': user_profile['email'],
        }
        if 'phone' in user_profile:
            slack_users[m['name']]['phone'] = normalize_phone_number(user_profile['phone'])

    connection = db.connect()
    # cache mode ids
    cursor = connection.cursor()
    cursor.execute('SELECT `id`, `name` FROM `contact_mode`')
    mode_ids = {row[1]: row[0] for row in cursor}
    cursor.close()

    slack_usernames = set(slack_users.keys())
    oncall_usernames = set(fetch_oncall_usernames(connection))

    users_to_insert = slack_usernames - oncall_usernames
    users_to_delete = oncall_usernames - slack_usernames

    logger.info('users to insert: %s', users_to_insert)
    logger.info('users to delete: %s', users_to_delete)

    insert_users(connection, slack_users, users_to_insert, mode_ids)
    delete_users(connection, users_to_delete)
    connection.close()


def main(config):
    slack_config = config.get('slack')
    if not slack_config:
        logger.error('slack config not found!')
        return

    oauth_access_token = slack_config.get('oauth_access_token')
    if not oauth_access_token:
        logger.error('slack oauth_access_token not found!')
        return

    slack_client = SlackClient(oauth_access_token)
    sync_cycle = config['user_sync'].get('cycle', 60 * 60)

    while True:
        start = time.time()
        sync_action(slack_client)
        duration = time.time() - start
        logger.info('Slack user sync finished, took %ss, sleep for %ss.',
                    duration, sync_cycle - duration)
        sleep(sync_cycle - duration)
