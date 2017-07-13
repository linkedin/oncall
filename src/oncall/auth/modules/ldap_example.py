# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import ldap


class Authenticator:
    def __init__(self, config):
        if config.get('debug'):
            self.authenticate = self.debug_auth
            return
        self.ldap_url = config['ldap_url']
        self.cert_path = config['ldap_cert_path']
        self.user_suffix = config['ldap_user_suffix']
        self.authenticate = self.ldap_auth

    def ldap_auth(self, username, password):
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.cert_path)
        connection = ldap.initialize(self.ldap_url)
        connection.set_option(ldap.OPT_REFERRALS, 0)

        try:
            if password:
                connection.simple_bind_s(username + self.user_suffix, password)
            else:
                return False
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.SERVER_DOWN:
            return None
        return True

    def debug_auth(self, username, password):
        return True
