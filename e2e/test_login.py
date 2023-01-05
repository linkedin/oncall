# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from beaker.middleware import SessionMiddleware
from falcon.testing import TestCase
from oncall.app import ReqBodyMiddleware
import falcon

from oncall import db
from oncall.auth import (
    login, logout, login_required, check_user_auth, check_team_auth
)


class TestLogin(TestCase):
    config = {'auth': {'ldap_cert_path': 'ldap_cert.pem',
                       'ldap_url': 'ldaps://lca1-ldap-vip.corp.linkedin.com',
                       'ldap_user_suffix': '@linkedin.biz',
                       'module': 'ldap'},
              'db': {'conn': {'kwargs': {'charset': 'utf8',
                                         'database': 'oncall-api',
                                         'echo': True,
                                         'host': '127.0.0.1',
                                         'scheme': 'mysql+pymysql',
                                         'user': 'root'},
                              'str': '%(scheme)s://%(user)s@%(host)s/%(database)s?charset=%(charset)s'},
                     'kwargs': {'pool_recycle': 3600}},
              'server': {'host': '0.0.0.0', 'port': 8080},
              'debug': True,
              'session': {'encrypt_key': 'abc', 'sign_key': '123'}}

    session_opts = {
        'session.type': 'cookie',
        'session.key': 'oncall-auth',
        # 'session.httponly': True,
        'session.encrypt_key': config['session']['encrypt_key'],
        'session.validate_key': config['session']['sign_key'],
        'session.crypto_type': 'cryptography'
    }

    class UserDummy(object):
        @login_required
        def on_get(self, req, resp, user):
            check_user_auth(user, req)

    class TeamDummy(object):
        @login_required
        def on_get(self, req, resp, team):
            check_team_auth(team, req)

    class DummyAuthenticator(object):
        def authenticate(self, username, password):
            return True

    def setUp(self):
        super(TestLogin, self).setUp()
        login.auth_manager = self.DummyAuthenticator()
        api = falcon.App(middleware=[
            ReqBodyMiddleware(),
        ])
        api.req_options.auto_parse_form_urlencoded = False
        self.app = api
        self.app.add_route('/login', login)
        self.app.add_route('/logout', logout)
        self.app.add_route('/dummy/{user}', self.UserDummy())
        self.app.add_route('/dummy2/{team}', self.TeamDummy())
        self.app = SessionMiddleware(self.app, self.session_opts)

        self.user_name = 'test_login_user'
        self.admin_name = 'test_login_admin'
        self.team_name = 'test_login_team'

        connection = db.connect()
        cursor = connection.cursor()
        # Create users
        cursor.execute("INSERT INTO `user` (`name`, `active`) VALUES (%s, 1)", self.user_name)
        self.user_id = cursor.lastrowid
        cursor.execute("INSERT INTO `user` (`name`, `active`) VALUES (%s, 1)", self.admin_name)
        self.admin_id = cursor.lastrowid

        # Set up team
        cursor.execute("INSERT INTO `team` (`name`) VALUES (%s)", self.team_name)
        self.team_id = cursor.lastrowid
        cursor.execute("INSERT INTO `team_user` VALUES (%s, %s)", (self.team_id, self.user_id))
        cursor.execute("INSERT INTO `team_user` VALUES (%s, %s)", (self.team_id, self.admin_id))
        cursor.execute("INSERT INTO `team_admin` VALUES (%s, %s)", (self.team_id, self.admin_id))

        connection.commit()
        cursor.close()
        connection.close()

    def tearDown(self):
        connection = db.connect()
        cursor = connection.cursor()

        cursor.execute("DELETE FROM `team` WHERE `name` = %s", self.team_name)
        cursor.execute("DELETE FROM `user` WHERE `name` IN %s", ([self.user_name, self.admin_name],))

        connection.commit()
        cursor.close()
        connection.close()

    def test_user_auth(self):
        # Test no login
        re = self.simulate_get('/dummy/'+self.user_name)
        assert re.status_code == 401

        # For tests below, put username/password into query string to
        # simulate a xxx-form-urlencoded form post
        # Test good login, auth check on self
        re = self.simulate_post('/login', body='username=%s&password=abc' % self.user_name)
        assert re.status_code == 200
        cookies = re.headers.get('set-cookie')
        token = str(re.json['csrf_token'])
        re = self.simulate_get('/dummy/'+self.user_name, headers={'X-CSRF-TOKEN': token, 'Cookie': cookies})
        assert re.status_code == 200

        # Test good login, auth check on manager
        re = self.simulate_post('/login', body='username=%s&password=abc' % self.admin_name)
        assert re.status_code == 200
        cookies = re.headers.get('set-cookie')
        token = str(re.json['csrf_token'])
        re = self.simulate_get('/dummy/'+self.user_name, headers={'X-CSRF-TOKEN': token, 'Cookie': cookies})
        assert re.status_code == 200

    def test_team_auth(self):
        # Test good login, auth check on manager
        re = self.simulate_post('/login', body='username=%s&password=abc' % self.admin_name)
        assert re.status_code == 200
        cookies = re.headers.get('set-cookie')
        token = str(re.json['csrf_token'])
        re = self.simulate_get('/dummy2/'+self.team_name, headers={'X-CSRF-TOKEN': token, 'Cookie': cookies})
        assert re.status_code == 200

    def test_logout(self):
        re = self.simulate_post('/login', body='username=%s&password=abc' % self.user_name)
        cookies = re.headers.get('set-cookie')
        assert re.status_code == 200
        token = str(re.json['csrf_token'])
        try:
            re = self.simulate_post('/logout', headers={'X-CSRF-TOKEN': token, 'Cookie': cookies})
        except KeyError:
            # FIXME: remove this try except after
            # https://github.com/falconry/falcon/pull/957 is merged
            pass
        assert re.status_code == 200
        re = self.simulate_get('/dummy/'+self.user_name, headers={'X-CSRF-TOKEN': token, 'Cookie': cookies})
        assert re.status_code == 401

    def test_csrf(self):
        # Test good login, auth check on manager
        re = self.simulate_post('/login', body='username=%s&password=abc' % self.admin_name)
        assert re.status_code == 200
        cookies = re.headers.get('set-cookie')
        re = self.simulate_get('/dummy2/'+self.team_name, headers={'X-CSRF-TOKEN': 'foo', 'Cookie': cookies})
        assert re.status_code == 401
