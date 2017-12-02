import logging
from gevent import sleep


from oncall import db, messengers

logger = logging.getLogger(__name__)


def user_validator(config):
    subject = config['subject']
    body = config['body']
    sleep_time = config.get('interval', 86400)
    while 1:
        # Sleep first so bouncing notifier doesn't spam
        sleep(sleep_time)
        connection = db.connect()
        cursor = connection.cursor()
        cursor.execute('''SELECT `user`.`name`
                          FROM `event` LEFT JOIN `user_contact` ON `event`.`user_id` = `user_contact`.`user_id`
                              AND `user_contact`.`mode_id` = (SELECT `id` FROM `contact_mode` WHERE `name` = 'call')
                          JOIN `user` ON `event`.`user_id` = `user`.`id`
                          WHERE `event`.`start` > UNIX_TIMESTAMP() AND `user_contact`.`destination` IS NULL
                          GROUP BY `event`.`user_id`;''')
        for row in cursor:
            message = {'user': row[0],
                       'mode': 'email',
                       'subject': subject,
                       'body': body}
            messengers.send_message(message)
        connection.close()
        cursor.close()
