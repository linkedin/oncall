#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import bcrypt
import getpass
import logging
import logging.handlers
import os
import sys
from oncall import utils, db
from oncall.auth.modules.db_auth import Authenticator

logger = logging.getLogger()


def setup_logger():
    logging.getLogger('requests').setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s')

    log_file = os.environ.get('USER_UPDATE_LOG_FILE')
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
    parser = argparse.ArgumentParser(description="Update an existing user.")
    parser.add_argument('config', metavar='C', help="The config file used by the app.")
    parser.add_argument('--name', required=True, help="The username to create.")
    parser.add_argument('--password-stdin', action='store_true', help="Read the password from stdin.")
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
        elif not password1 or authenticator.check_password_strength(password1):
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

    if password:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)
    else:
        hashed_password = None

    db.init(config['db'])
    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute("UPDATE `user` SET hashed_password = %s WHERE name = %s", (
                       hashed_password,
                       args.name,
                   ))
    connection.commit()
    cursor.close()
    connection.close()


if __name__ == '__main__':
    main()
