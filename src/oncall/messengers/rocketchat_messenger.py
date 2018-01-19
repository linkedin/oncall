import requests
import time
from oncall.constants import ROCKET_SUPPORT
from oncall import db


class rocketchat_messenger(object):
    supports = frozenset([ROCKET_SUPPORT])

    def __init__(self, config):
        self.user = config['user']
        self.password = config['password']
        self.api_host = config['api_host']
        self.refresh = config.get('refresh', 2592000)  # default 30 days
        self.last_auth = None
        self.token = None
        self.user_id = None
        self.authenticate()

    def authenticate(self):
        self.last_auth = time.time()
        re = requests.post(self.api_host + '/api/v1/login',
                           json={'username': self.user, 'password': self.password})
        data = re.json()
        if re.status_code != 200 or data['status'] != 'success':
            raise ValueError('Invalid RocketChat credentials')
        self.token = data['data']['authToken']
        self.user_id = data['data']['userId']

    def send(self, message):
        if time.time() - self.last_auth > self.refresh:
            self.authenticate()
        connection = db.connect()
        cursor = connection.cursor()
        try:
            cursor.execute('''SELECT `destination` FROM `user_contact`
                              WHERE `user_id` = (SELECT `id` FROM `user` WHERE `name` = %s)
                              AND `mode_id` = (SELECT `id` FROM `contact_mode` WHERE `name` = 'rocketchat')''',
                           message['user'])
            if cursor.rowcount == 0:
                raise ValueError('Rocketchat username not found for %s' % message['user'])
            target = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()
        re = requests.post(self.api_host + '/api/v1/chat.postMessage',
                           json={'channel': '@%s' % target,
                                 'text': ' -- '.join([message['subject'], message['body']])},
                           headers={'X-User-Id': self.user_id,
                                    'X-Auth-Token': self.token})
        if re.status_code != 200 or not re.json()['success']:
            raise ValueError('Failed to contact rocketchat')
