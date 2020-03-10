from gevent import monkey, sleep, spawn
monkey.patch_all()  # NOQA

import sys
import time
import yaml
import logging
import ldap

from oncall import metrics
from ldap.controls import SimplePagedResultsControl
from datetime import datetime
from pytz import timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from phonenumbers import format_number, parse, PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException


logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(ch)

stats = {
    'ldap_found': 0,
    'sql_errors': 0,
    'users_added': 0,
    'users_failed_to_add': 0,
    'users_failed_to_update': 0,
    'users_purged': 0,
    'user_contacts_updated': 0,
    'user_names_updated': 0,
    'user_photos_updated': 0,
    'users_reactivated': 0,
    'users_failed_to_reactivate': 0,
}

LDAP_SETTINGS = {}


def normalize_phone_number(num):
    return format_number(parse(num.decode('utf-8'), 'US'), PhoneNumberFormat.INTERNATIONAL)


def get_predefined_users(config):
    users = {}

    try:
        config_users = config['sync_script']['preset_users']
    except KeyError:
        return {}

    for user in config_users:
        users[user['name']] = user
        for key in ['sms', 'call']:
            try:
                users[user['name']][key] = normalize_phone_number(users[user['name']][key])
            except (NumberParseException, KeyError, AttributeError):
                users[user['name']][key] = None

    return users


def timestamp_to_human_str(timestamp, tz):
    dt = datetime.fromtimestamp(timestamp, timezone(tz))
    return ' '.join([dt.strftime('%Y-%m-%d %H:%M:%S'), tz])


def prune_user(engine, username):
    global stats
    stats['users_purged'] += 1

    try:
        engine.execute('DELETE FROM `user` WHERE `name` = %s', username)
        logger.info('Deleted inactive user %s', username)

    # The user has messages or some other user data which should be preserved. Just mark as inactive.
    except IntegrityError:
        logger.info('Marking user %s inactive', username)
        engine.execute('UPDATE `user` SET `active` = FALSE WHERE `name` = %s', username)

    except SQLAlchemyError as e:
        logger.error('Deleting user %s failed: %s', username, e)
        stats['sql_errors'] += 1

    try:
        engine.execute('DELETE FROM `ical_key` WHERE `requester` = %s', username)
        logger.info('Invalidated ical_key of inactive user %s', username)
    except Exception as e:
        logger.error('Invalidating ical_key of inactive user %s failed: %s', username, e)
        stats['sql_errors'] += 1


def fetch_ldap():
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
    l = ldap.initialize(LDAP_SETTINGS['url'])
    if 'cert_path' in LDAP_SETTINGS:
        l.set_option(ldap.OPT_X_TLS_CACERTFILE, LDAP_SETTINGS['cert_path'])
    l.simple_bind_s(LDAP_SETTINGS['user'], LDAP_SETTINGS['password'])

    req_ctrl = SimplePagedResultsControl(True, size=1000, cookie='')

    known_ldap_resp_ctrls = {
        SimplePagedResultsControl.controlType: SimplePagedResultsControl,
    }

    base = LDAP_SETTINGS['base']
    attrs = ['distinguishedName'] + list(LDAP_SETTINGS['attrs'].values())
    query = LDAP_SETTINGS['query']

    users = {}
    dn_map = {}

    while True:
        msgid = l.search_ext(base, ldap.SCOPE_SUBTREE, query, attrs, serverctrls=[req_ctrl])
        rtype, rdata, rmsgid, serverctrls = l.result3(msgid, resp_ctrl_classes=known_ldap_resp_ctrls)
        logger.info('Loaded %d entries from ldap.' % len(rdata))
        for dn, ldap_dict in rdata:
            if LDAP_SETTINGS['attrs']['mail'] not in ldap_dict:
                logger.error('ERROR: invalid ldap entry for dn: %s' % dn)
                continue

            try:
                username_field = LDAP_SETTINGS['attrs']['username']
            except KeyError:
                username_field = "sAMAccountName"

            username = ldap_dict[username_field][0]

            mobile = ldap_dict.get(LDAP_SETTINGS['attrs']['mobile'])
            mail = ldap_dict.get(LDAP_SETTINGS['attrs']['mail'])
            name = ldap_dict.get(LDAP_SETTINGS['attrs']['full_name'])[0]

            if mobile:
                try:
                    mobile = normalize_phone_number(mobile[0])
                except NumberParseException:
                    mobile = None
                except UnicodeEncodeError:
                    mobile = None

            if mail:
                mail = mail[0]
                slack = mail.split('@')[0]
            else:
                slack = None

            contacts = {'call': mobile, 'sms': mobile, 'email': mail, 'slack': slack, 'name': name}
            dn_map[dn] = username
            users[username] = contacts

        pctrls = [
            c for c in serverctrls if c.controlType == SimplePagedResultsControl.controlType
        ]

        cookie = pctrls[0].cookie
        if not cookie:
            break
        req_ctrl.cookie = cookie

    return users


def user_exists(username, engine):
    return engine.execute('SELECT `id` FROM user WHERE name = %s', username)


def import_user(username, ldap_contacts, engine):
    logger.debug('Inserting %s' % username)
    full_name = ldap_contacts.pop('full_name')
    user_add_sql = 'INSERT INTO `user` (`name`, `full_name`, `photo_url`) VALUES (%s, %s, %s)'

    # get objects needed for insertion
    modes = get_modes(engine)

    try:
        photo_url_tpl = LDAP_SETTINGS.get('image_url')
        photo_url = photo_url_tpl % username if photo_url_tpl else None
        engine.execute(user_add_sql, (username, full_name, photo_url))
        engine.execute("SELECT `id` FROM user WHERE name = %s", username)
        row = engine.fetchone()
        user_id = row['id']
    except SQLAlchemyError:
        stats['users_failed_to_add'] += 1
        stats['sql_errors'] += 1
        logger.exception('Failed to add user %s' % username)
        return
    stats['users_added'] += 1
    for key, value in ldap_contacts.items():
        if value and key in modes:
            logger.debug('\t%s -> %s' % (key, value))
            user_contact_add_sql = 'INSERT INTO `user_contact` (`user_id`, `mode_id`, `destination`) VALUES (%s, %s, %s)'
            engine.execute(user_contact_add_sql, (user_id, modes[key], value))


def get_modes(engine):
    engine.execute('SELECT `name`, `id` FROM `contact_mode`')
    modes = {}
    for row in engine.fetchall():
        modes[row['name']] = row['id']
    return modes


def update_user(username, ldap_contacts, engine):
    oncall_user = get_oncall_user(username, engine)
    db_contacts = oncall_user[username]
    full_name = ldap_contacts.pop('full_name')

    contact_update_sql = 'UPDATE user_contact SET destination = %s WHERE user_id = (SELECT id FROM user WHERE name = %s) AND mode_id = %s'
    contact_insert_sql = 'INSERT INTO user_contact (user_id, mode_id, destination) VALUES ((SELECT id FROM user WHERE name = %s), %s, %s)'
    contact_delete_sql = 'DELETE FROM user_contact WHERE user_id = (SELECT id FROM user WHERE name = %s) AND mode_id = %s'
    name_update_sql = 'UPDATE user SET full_name = %s WHERE name = %s'
    photo_update_sql = 'UPDATE user SET photo_url = %s WHERE name = %s'

    modes = get_modes(engine)

    try:
        if full_name != db_contacts.get('full_name'):
            engine.execute(name_update_sql, (full_name, username))
            stats['user_names_updated'] += 1
        if 'image_url' in LDAP_SETTINGS and not db_contacts.get('photo_url'):
            photo_url_tpl = LDAP_SETTINGS.get('image_url')
            photo_url = photo_url_tpl % username if photo_url_tpl else None
            engine.execute(photo_update_sql, (photo_url, username))
            stats['user_photos_updated'] += 1
        for mode in modes:
            if mode in ldap_contacts and ldap_contacts[mode]:
                if mode in db_contacts:
                    if ldap_contacts[mode] != db_contacts[mode]:
                        logger.debug('\tupdating %s (%s -> %s)' % (mode, db_contacts[mode], ldap_contacts[mode]))
                        engine.execute(contact_update_sql, (ldap_contacts[mode], username, modes[mode]))
                        stats['user_contacts_updated'] += 1
                else:
                    logger.debug('\tadding %s', mode)
                    engine.execute(contact_insert_sql, (username, modes[mode], ldap_contacts[mode]))
                    stats['user_contacts_updated'] += 1
            elif mode in db_contacts:
                logger.debug('\tdeleting %s', mode)
                engine.execute(contact_delete_sql, (username, modes[mode]))
                stats['user_contacts_updated'] += 1
            else:
                logger.debug('\tmissing %s', mode)
    except SQLAlchemyError:
        stats['users_failed_to_update'] += 1
        stats['sql_errors'] += 1
        logger.exception('Failed to update user %s' % username)


def get_oncall_user(username, engine):
    oncall_user = {}
    user_query = '''SELECT `user`.`name` as `name`, `contact_mode`.`name` as `mode`, `user_contact`.`destination`,
                            `user`.`full_name`, `user`.`photo_url`
                     FROM `user`
                     LEFT OUTER JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
                     LEFT OUTER JOIN `contact_mode` ON `user_contact`.`mode_id` = `contact_mode`.`id`
                     WHERE `user`.`name` = %s
                     ORDER BY `user`.`name`'''
    engine.execute(user_query, username)
    for row in engine.fetchall():
        contacts = oncall_user.setdefault(row['name'], {})
        if row['mode'] is None or row['destination'] is None:
            continue
        contacts[row['mode']] = row['destination']
        contacts['full_name'] = row['full_name']
        contacts['photo_url'] = row['photo_url']

    return oncall_user


def sync(config, engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    oncall_users = {}
    users_query = '''SELECT `user`.`name` as `name`, `contact_mode`.`name` as `mode`, `user_contact`.`destination`,
                            `user`.`full_name`, `user`.`photo_url`
                     FROM `user`
                     LEFT OUTER JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`
                     LEFT OUTER JOIN `contact_mode` ON `user_contact`.`mode_id` = `contact_mode`.`id`
                     ORDER BY `user`.`name`'''
    for row in engine.execute(users_query):
        contacts = oncall_users.setdefault(row.name, {})
        if row.mode is None or row.destination is None:
            continue
        contacts[row.mode] = row.destination
        contacts['full_name'] = row.full_name
        contacts['photo_url'] = row.photo_url

    oncall_usernames = set(oncall_users)

    # users from ldap and config file
    ldap_users = fetch_ldap()
    stats['ldap_found'] += len(ldap_users)
    ldap_users.update(get_predefined_users(config))
    ldap_usernames = set(ldap_users)

    # set of ldap users not in oncall
    users_to_insert = ldap_usernames - oncall_usernames
    # set of existing oncall users that are in ldap
    users_to_update = oncall_usernames & ldap_usernames
    # set of users in oncall but not ldap, assumed to be inactive
    inactive_users = oncall_usernames - ldap_usernames
    # users who need to be deactivated
    if inactive_users:
        rows = engine.execute('SELECT name FROM user WHERE active = TRUE AND name IN %s', inactive_users)
        users_to_purge = (user.name for user in rows)
    else:
        users_to_purge = []

    # set of inactive oncall users who appear in ldap
    rows = engine.execute('SELECT name FROM user WHERE active = FALSE AND name IN %s', ldap_usernames)
    users_to_reactivate = (user.name for user in rows)

    # get objects needed for insertion
    modes = dict(list(session.execute('SELECT `name`, `id` FROM `contact_mode`')))

    user_add_sql = 'INSERT INTO `user` (`name`, `full_name`, `photo_url`) VALUES (%s, %s, %s)'

    # insert users that need to be
    logger.debug('Users to insert:')
    for username in users_to_insert:
        logger.debug('Inserting %s' % username)
        full_name = ldap_users[username].pop('name')
        try:
            photo_url_tpl = LDAP_SETTINGS.get('image_url')
            photo_url = photo_url_tpl % username if photo_url_tpl else None
            user_id = engine.execute(user_add_sql, (username, full_name, photo_url)).lastrowid
        except SQLAlchemyError:
            stats['users_failed_to_add'] += 1
            stats['sql_errors'] += 1
            logger.exception('Failed to add user %s' % username)
            continue
        stats['users_added'] += 1
        for key, value in ldap_users[username].items():
            if value and key in modes:
                logger.debug('\t%s -> %s' % (key, value))
                user_contact_add_sql = 'INSERT INTO `user_contact` (`user_id`, `mode_id`, `destination`) VALUES (%s, %s, %s)'
                engine.execute(user_contact_add_sql, (user_id, modes[key], value))

    # update users that need to be
    contact_update_sql = 'UPDATE user_contact SET destination = %s WHERE user_id = (SELECT id FROM user WHERE name = %s) AND mode_id = %s'
    contact_insert_sql = 'INSERT INTO user_contact (user_id, mode_id, destination) VALUES ((SELECT id FROM user WHERE name = %s), %s, %s)'
    contact_delete_sql = 'DELETE FROM user_contact WHERE user_id = (SELECT id FROM user WHERE name = %s) AND mode_id = %s'
    name_update_sql = 'UPDATE user SET full_name = %s WHERE name = %s'
    photo_update_sql = 'UPDATE user SET photo_url = %s WHERE name = %s'
    logger.debug('Users to update:')
    for username in users_to_update:
        logger.debug(username)
        try:
            db_contacts = oncall_users[username]
            ldap_contacts = ldap_users[username]
            full_name = ldap_contacts.pop('name')
            if full_name != db_contacts.get('full_name'):
                engine.execute(name_update_sql, (full_name, username))
                stats['user_names_updated'] += 1
            if 'image_url' in LDAP_SETTINGS and not db_contacts.get('photo_url'):
                photo_url_tpl = LDAP_SETTINGS.get('image_url')
                photo_url = photo_url_tpl % username if photo_url_tpl else None
                engine.execute(photo_update_sql, (photo_url, username))
                stats['user_photos_updated'] += 1
            for mode in modes:
                if mode in ldap_contacts and ldap_contacts[mode]:
                    if mode in db_contacts:
                        if ldap_contacts[mode] != db_contacts[mode]:
                            logger.debug('\tupdating %s', mode)
                            engine.execute(contact_update_sql, (ldap_contacts[mode], username, modes[mode]))
                            stats['user_contacts_updated'] += 1
                    else:
                        logger.debug('\tadding %s', mode)
                        engine.execute(contact_insert_sql, (username, modes[mode], ldap_contacts[mode]))
                        stats['user_contacts_updated'] += 1
                elif mode in db_contacts:
                    logger.debug('\tdeleting %s', mode)
                    engine.execute(contact_delete_sql, (username, modes[mode]))
                    stats['user_contacts_updated'] += 1
                else:
                    logger.debug('\tmissing %s', mode)
        except SQLAlchemyError:
            stats['users_failed_to_update'] += 1
            stats['sql_errors'] += 1
            logger.exception('Failed to update user %s' % username)
            continue

    logger.debug('Users to mark as inactive:')
    for username in users_to_purge:
        prune_user(engine, username)

    logger.debug('Users to reactivate:')
    for username in users_to_reactivate:
        logger.debug(username)
        try:
            engine.execute('UPDATE user SET active = TRUE WHERE name = %s', username)
            stats['users_reactivated'] += 1
        except SQLAlchemyError:
            stats['users_failed_to_reactivate'] += 1
            stats['sql_errors'] += 1
            logger.exception('Failed to reactivate user %s', username)

    session.commit()
    session.close()


def metrics_sender():
    while True:
        metrics.emit_metrics()
        sleep(60)


def main(config):
    global LDAP_SETTINGS

    LDAP_SETTINGS = config['ldap_sync']

    metrics.init(config, 'oncall-ldap-user-sync', stats)
    spawn(metrics_sender)
    # Default sleep one hour
    sleep_time = config.get('user_sync_sleep_time', 3600)
    engine = create_engine(config['db']['conn']['str'] % config['db']['conn']['kwargs'],
                           **config['db']['kwargs'])
    while 1:
        logger.info('Starting user sync loop at %s' % time.time())
        sync(config, engine)
        logger.info('Sleeping for %s seconds' % sleep_time)
        sleep(sleep_time)


if __name__ == '__main__':
    config_path = sys.argv[1]
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    main(config)
