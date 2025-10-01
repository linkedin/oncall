import time
import logging
from gevent import sleep
from ujson import dumps as json_dumps
from datetime import datetime
from pytz import timezone
from oncall import db, constants

logger = logging.getLogger(__name__)

HOUR = 60 * 60
DAY = HOUR * 24
WEEK = DAY * 7


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


def check_user_contact_info(user_id, cursor):
    """Check if user has complete contact information (phone number for SMS/call)"""
    # Check if user has SMS contact info
    cursor.execute('''SELECT destination FROM user_contact
                      WHERE user_id = %s AND mode_id = (SELECT id FROM contact_mode WHERE name = 'sms')''',
                   (user_id,))
    sms_contact = cursor.fetchone()

    # Check if user has call contact info
    cursor.execute('''SELECT destination FROM user_contact
                      WHERE user_id = %s AND mode_id = (SELECT id FROM contact_mode WHERE name = 'call')''',
                   (user_id,))
    call_contact = cursor.fetchone()

    missing_contacts = []
    if not sms_contact:
        missing_contacts.append('SMS Number')
    if not call_contact:
        missing_contacts.append('Call Number')

    return missing_contacts


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


def reminder(config):
    interval = config['polling_interval']
    default_timezone = config['default_timezone']

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT `last_window_end` FROM `notifier_state`')
    if cursor.rowcount != 1:
        window_start = int(time.time() - interval)
        logger.warning('Corrupted/missing notifier state; unable to determine last window. Guessing %s. Creating state in database',
                       window_start)
        # create a clean state in the datebase
        cursor.execute('DELETE FROM `notifier_state`')
        cursor.execute('INSERT INTO `notifier_state` (`last_window_end`) VALUES (%s) ', window_start)
        connection.commit()
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
            WHERE `e`.`id` IS NULL AND `user`.`active` = 1
    '''

    while (1):
        logger.info('Reminder polling loop started')
        window_end = int(time.time())

        connection = db.connect()
        cursor = connection.cursor(db.DictCursor)

        cursor.execute(query, (constants.ONCALL_REMINDER, window_start, window_end))
        notifications = cursor.fetchall()

        for row in notifications:
            # Check if user has missing contact information
            missing_contacts = check_user_contact_info(row['user_id'], cursor)

            context = {'team': row['team'],
                       'start_time': timestamp_to_human_str(row['start'],
                                                            row['time_zone'] if row['time_zone'] else default_timezone),
                       'time_before': sec_to_human_str(row['time_before']),
                       'role': row['role']}

            # Add contact update message if missing contact info
            if missing_contacts:
                contact_warning = (
                    f"\n\nIMPORTANT: Your contact information is incomplete. "
                    f"Please update your {', '.join(missing_contacts)} in your profile "
                    f"ASAP to ensure you receive critical notifications."
                )
                context['contact_warning'] = contact_warning
                logger.warning('User %s has missing contact information: %s', row['name'], ', '.join(missing_contacts))

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
