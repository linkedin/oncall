# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.


from oncall.constants import EMAIL_SUPPORT, SMS_SUPPORT, CALL_SUPPORT
from iris.client import IrisClient


class iris_messenger(object):
    supports = frozenset([EMAIL_SUPPORT, SMS_SUPPORT, CALL_SUPPORT])

    def __init__(self, config):
        self.config = config
        self.iris_client = IrisClient(config['application'], config['iris_api_key'])

    def send(self, message):
        self.iris_client.notification(role='user', target=message['user'], priority=message.get('priority'),
                                      mode=message.get('mode'), subject=message['subject'], body=message['body'])
