# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from datetime import datetime as dt
from ... import db
from icalendar import Calendar, Event, vCalAddress, vText
from pytz import utc


def events_to_ical(events, identifier, contact=True):
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)

    ical = Calendar()
    ical.add('calscale', 'GREGORIAN')
    ical.add('prodid', '-//Oncall//Oncall calendar feed//EN')
    ical.add('version', '2.0')
    ical.add('x-wr-calname', '%s Oncall Calendar' % identifier)

    users = {}

    for event in events:
        username = event['user']
        if username not in users:
            if contact:
                cursor.execute('''
                    SELECT
                        `user`.`full_name` AS full_name,
                        `contact_mode`.`name` AS contact_mode,
                        `user_contact`.`destination` AS destination
                    FROM `user_contact`
                    JOIN `contact_mode` ON `contact_mode`.`id` = `user_contact`.`mode_id`
                    JOIN `user` ON `user`.`id` = `user_contact`.`user_id`
                    WHERE `user`.`name` = %s
                ''', username)
            else:
                cursor.execute('''
                    SELECT `user`.`full_name` AS full_name
                    FROM `user`
                    WHERE `user`.`name` = %s
                ''', username)

            info = {'username': username, 'contacts': {}}
            for row in cursor:
                info['full_name'] = row['full_name']
                if contact:
                    info['contacts'][row['contact_mode']] = row['destination']
            users[username] = info
        user = users[username]

        # Create the event itself
        full_name = user.get('full_name', user['username'])
        cal_event = Event()
        cal_event.add('uid', 'event-%s@oncall' % event['id'])
        cal_event.add('dtstart', dt.fromtimestamp(event['start'], utc))
        cal_event.add('dtend', dt.fromtimestamp(event['end'], utc))
        cal_event.add('dtstamp', dt.utcnow())
        cal_event.add('summary',
                      '%s %s shift: %s' % (event['team'], event['role'], full_name))
        cal_event.add('description',
                      '%s\n' % full_name +
                      ('\n'.join(['%s: %s' % (mode, dest) for mode, dest in user['contacts'].items()]) if contact else ''))
        cal_event.add('TRANSP', 'TRANSPARENT')

        # Attach info about the user oncall
        attendee = vCalAddress('MAILTO:%s' % (user['contacts'].get('email') if contact else ''))
        attendee.params['cn'] = vText(full_name)
        attendee.params['ROLE'] = vText('REQ-PARTICIPANT')
        cal_event.add('attendee', attendee, encode=0)

        ical.add_component(cal_event)

    cursor.close()
    connection.close()
    return ical.to_ical()
