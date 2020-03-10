# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db


def get_name_and_type_from_key(key):
    connection = db.connect()
    cursor = connection.cursor()

    result = None
    cursor.execute(
        '''
        SELECT `name`, `type`
        FROM `ical_key`
        WHERE `key` = %s
        ''',
        (key, ))
    if cursor.rowcount != 0:
        row = cursor.fetchone()
        result = (row[0], row[1])

    cursor.close()
    connection.close()
    return result


def get_ical_key(requester, name, type):
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT `key`
        FROM `ical_key`
        WHERE
            `requester` = %s AND
            `name` = %s AND
            `type` = %s
        ''',
        (requester, name, type))
    if cursor.rowcount == 0:
        key = None
    else:
        key = cursor.fetchone()[0]

    cursor.close()
    connection.close()
    return key


def update_ical_key(requester, name, type, key):
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        '''
        INSERT INTO `ical_key` (`key`, `requester`, `name`, `type`, `time_created`)
        VALUES (%s, %s, %s, %s, UNIX_TIMESTAMP())
        ON DUPLICATE KEY UPDATE `key` = %s, `time_created` = UNIX_TIMESTAMP()
        ''',
        (key, requester, name, type, key))
    connection.commit()

    cursor.close()
    connection.close()


def delete_ical_key(requester, name, type):
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        '''
        DELETE FROM `ical_key`
        WHERE
            `requester` = %s AND
            `name` = %s AND
            `type` = %s
        ''',
        (requester, name, type))
    connection.commit()

    cursor.close()
    connection.close()


#####
# admin actions below
#####


def get_ical_key_detail(key):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute(
        '''
        SELECT `requester`, `name`, `type`, `time_created`
        FROM `ical_key`
        WHERE `key` = %s
        ''',
        (key, ))
    # fetchall because we may want to know if there is any key (uuid) collision
    results = cursor.fetchall()

    cursor.close()
    connection.close()
    return results


def get_ical_key_detail_by_requester(requester):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    cursor.execute(
        '''
        SELECT `key`, `name`, `type`, `time_created`
        FROM `ical_key`
        WHERE `requester` = %s
        ''',
        (requester, ))
    results = cursor.fetchall()

    cursor.close()
    connection.close()
    return results


def invalidate_ical_key(key):
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        '''
        DELETE FROM `ical_key`
        WHERE
            `key` = %s
        ''',
        (key, ))
    connection.commit()

    cursor.close()
    connection.close()


def invalidate_ical_key_by_requester(requester):
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute(
        '''
        DELETE FROM `ical_key`
        WHERE
            `requester` = %s
        ''',
        (requester, ))
    connection.commit()

    cursor.close()
    connection.close()
