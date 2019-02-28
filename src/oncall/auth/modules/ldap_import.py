# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import ldap
from oncall import db
import os
import logging
from oncall.user_sync.ldap_sync import user_exists, import_user, update_user

logger = logging.getLogger(__name__)


class Authenticator:
    def __init__(self, config):
        if config.get('debug'):
            self.authenticate = self.debug_auth
            return
        self.authenticate = self.ldap_auth

        if 'ldap_cert_path' in config:
            self.cert_path = config['ldap_cert_path']
            if not os.access(self.cert_path, os.R_OK):
                logger.error("Failed to read ldap_cert_path certificate")
                raise IOError
        else:
            self.cert_path = None

        self.bind_user = config.get('ldap_bind_user')
        self.bind_password = config.get('ldap_bind_password')
        self.search_filter = config.get('ldap_search_filter')

        self.ldap_url = config.get('ldap_url')
        self.base_dn = config.get('ldap_base_dn')

        self.user_suffix = config.get('ldap_user_suffix')
        self.import_user = config.get('import_user', False)
        self.attrs = config.get('attrs')

    def ldap_auth(self, username, password):
        if self.cert_path:
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.cert_path)

        connection = ldap.initialize(self.ldap_url)
        connection.set_option(ldap.OPT_REFERRALS, 0)
        attrs = ['dn'] + list(self.attrs.values())
        ldap_contacts = {}

        if not password:
            return False

        auth_user = username + self.user_suffix
        try:
            if self.bind_user:
                # use search filter to find DN of username
                connection.simple_bind_s(self.bind_user, self.bind_password)
                sfilter = self.search_filter % username
                result = connection.search_s(self.base_dn, ldap.SCOPE_SUBTREE, sfilter, attrs)
                if len(result) < 1:
                    return False
                auth_user = result[0][0]
                ldap_attrs = result[0][1]
                for key, val in self.attrs.items():
                    if ldap_attrs.get(val):
                        if type(ldap_attrs.get(val)) == list:
                            ldap_contacts[key] = ldap_attrs.get(val)[0]
                        else:
                            ldap_contacts[key] = ldap_attrs.get(val)
                    else:
                        ldap_contacts[key] = val

            connection.simple_bind_s(auth_user, password)

        except ldap.INVALID_CREDENTIALS:
            return False
        except (ldap.SERVER_DOWN, ldap.INVALID_DN_SYNTAX) as err:
            logger.warn("%s", err)
            return None

        if self.import_user:
            connection = db.connect()
            cursor = connection.cursor(db.DictCursor)
            if user_exists(username, cursor):
                logger.info("user %s already exists, updating from ldap", username)
                update_user(username, ldap_contacts, cursor)
            else:
                logger.info("user %s does not exists. importing.", username)
                import_user(username, ldap_contacts, cursor)
            connection.commit()
            cursor.close()
            connection.close()

        return True

    def debug_auth(self, username, password):
        return True
