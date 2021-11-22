#!/usr/bin/env python
# -*- coding:utf-8 -*-

from gevent import monkey, spawn
monkey.patch_all()  # NOQA

import argparse
import bcrypt
import getpass
import logging
import logging.handlers
import os
import sys
import importlib
from oncall import utils, db
from oncall.auth.modules.db_auth import Authenticator

logger = logging.getLogger()


def setup_logger():
    logging.getLogger('requests').setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s')

    log_file = os.environ.get('USER_PASSWORD_CREATE_LOG_FILE')
    if log_file:
        ch = logging.handlers.RotatingFileHandler(
            log_file, mode='a', maxBytes=10485760, backupCount=10)
    else:
        ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)


def parse_args():
    parser = argparse.ArgumentParser(description="Create a new user with local password.")
    parser.add_argument('config', metavar='C', help="The config file used by the app.")
    parser.add_argument('--name', required=True, help="The username to create.")
    parser.add_argument('--password-stdin', action='store_true', help="Read the password from stdin.")
    parser.add_argument('--inactive', action='store_true', help="Sets the user to 'inactive'.")
    parser.add_argument('--full-name', help="The full name of the user.")
    parser.add_argument('--time-zone', help="The time zone the user belongs to.")
    parser.add_argument('--photo-url', help="The URL where the user's photo can be found.")
    parser.add_argument('--is-god', action='store_true', help="Gives the user 'god' permissions.")
    return parser.parse_args()


def get_password(authenticator):
    password1 = ""
    while True:
        print("Please enter a password:")
        password1 = getpass.getpass()
        print("Please re-enter the password:")
        password2 = getpass.getpass()
        if password1 != password2:
            logging.error("The two passwords don't match")
        elif authenticator.check_password_strength(password1):
            break

    return password1


def main():
    setup_logger()
    args = parse_args()
    config = utils.read_config(args.config)
    authenticator = Authenticator(config)
    if args.password_stdin:
        password = sys.stdin.readline().rstrip()
        if not authenticator.check_password_strength(password):
            sys.exit(1)
    else:
        password = get_password(authenticator)

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password, salt)

    db.init(config['db'])
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute("INSERT into `user` (`name`, `hashed_password`, `active`, "
                   "`full_name`, `time_zone`, `photo_url`, `god`) VALUES "
                   "(%s, %s, %s, %s, %s, %s, %s)", (
                       args.name,
                       hashed_password,
                       int(not args.inactive),
                       args.full_name,
                       args.time_zone,
                       args.photo_url,
                       int(args.is_god),
                   ))
    connection.commit()
    cursor.close()
    connection.close()


if __name__ == '__main__':
    main()
