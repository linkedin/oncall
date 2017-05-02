from oncall.constants import EMAIL_SUPPORT, SMS_SUPPORT, CALL_SUPPORT
import logging

logger = logging.getLogger('dummy_messenger')


class dummy(object):
    supports = frozenset([EMAIL_SUPPORT, SMS_SUPPORT, CALL_SUPPORT])

    def __init__(self, config):
        pass

    def send(self, message):
        logger.info('sent message %s' % message)