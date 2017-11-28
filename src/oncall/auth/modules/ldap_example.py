# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import ldap
import logging

logger = logging.getLogger(__name__)

class Authenticator:
    def __init__(self, config):
        if config.get('debug'):
            self.authenticate = self.debug_auth
            return
        self.authenticate = self.ldap_auth

        if 'ldap_cert_path' in config:
            self.cert_path = config['ldap_cert_path']
            try:
                with open(self.cert_path) as fp:
                    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.cert_path)
            except IOError as err:
                logger.error("Failed to read cert_path: %s", err)
                return False

        if 'ldap_bind_user' in config:
            self.bind_user = config['ldap_bind_user']
            self.bind_password = config['ldap_bind_password']
            self.search_filter = config['ldap_search_filter']

        self.ldap_url = config['ldap_url']
        self.user_suffix = config['ldap_user_suffix']
        self.base_dn = config['ldap_base_dn']


    def ldap_auth(self, username, password):
        connection = ldap.initialize(self.ldap_url)
        connection.set_option(ldap.OPT_REFERRALS, 0)

        bind_user = username + self.user_suffix
        bind_password = password

        # override bind user and password if they have been specified in the config
        try:
            bind_user = self.bind_user
            bind_password = self.bind_password
        except AttributeError:
            pass

        try:
            if password:
                connection.simple_bind_s(bind_user, bind_password)
                if self.bind_user:
                    # use search filter to find DN
                    search_filter = self.search_filter % username
                    result = connection.search_s(self.base_dn, ldap.SCOPE_SUBTREE, search_filter, ['dn'])
                    user_dn = result[0][0]
                    connection.simple_bind_s(user_dn, password)
            else:
                return False
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.SERVER_DOWN as err:
            logger.warn("%s", err)
            return None
        return True


    def debug_auth(self, username, password):
        return True
