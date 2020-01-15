# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from collections import defaultdict
import logging
import importlib

logger = logging.getLogger()
_active_messengers = defaultdict(list)


class OncallMessengerException(Exception):
    pass


def init_messengers(messengers):
    for messenger in messengers:
        if '.' in messenger['type']:
            module_path = messenger['type']
            messenger['type'] = messenger['type'].split('.')[-1]
        else:
            module_path = 'oncall.messengers.' + messenger['type']

        instance = getattr(importlib.import_module(module_path), messenger['type'])(messenger)
        for transport in instance.supports:
            _active_messengers[transport].append(instance)


def send_message(message):
    for messenger in _active_messengers[message['mode']]:
        logger.debug('Attempting %s send using messenger %s', message['mode'], messenger)
        try:
            return messenger.send(message)
        except Exception:
            logger.exception('Sending %s with messenger %s failed', message, messenger)
            continue

    raise OncallMessengerException('All %s messengers failed for %s' % (message['mode'], message))
