# -*- coding: utf-8 -*-
import bcrypt
import logging
import re

from oncall import db

logger = logging.getLogger()


class Authenticator(object):
    def __init__(self, config):
        self.config = config

    def check_password_strength(self, password):
        if not password:
            logger.error("A password must be provided")
            return False

        rules = self.config["auth"].get('password_rules', [])
        for rule in rules:
            if not re.match(rule["rule"], password):
                logging.error(rule["message"])
                return False
        return True

    def authenticate(self, username, password):
        connection = db.connect()
        cursor = connection.cursor(db.DictCursor)

        cursor.execute("SELECT `hashed_password` FROM `user` WHERE `name` = %s", username)
        if cursor.rowcount != 1:
            cursor.close()
            connection.close()
            return False

        hashed_password = cursor.fetchone()["hashed_password"]
        if not hashed_password:
            # Ignore users without a password set
            cursor.close()
            connection.close()
            return False

        cursor.close()
        connection.close()
        return bcrypt.checkpw(password, hashed_password)
