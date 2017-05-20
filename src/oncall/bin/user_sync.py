#!/usr/bin/env python
# -*- coding:utf-8 -*-

from gevent import monkey, spawn
monkey.patch_all()  # NOQA

import logging
import os
import sys
import importlib
from oncall import utils, db

logger = logging.getLogger()


def setup_logger():
    logging.getLogger('requests').setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s')

    log_file = os.environ.get('USER_SYNC_LOG_FILE')
    if log_file:
        ch = logging.handlers.RotatingFileHandler(
            log_file, mode='a', maxBytes=10485760, backupCount=10)
    else:
        ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)


def main():
    setup_logger()
    config = utils.read_config(sys.argv[1])
    user_sync_config = config.get('user_sync')
    if not user_sync_config:
        sys.exit('user_sync config not found!')

    sync_module = user_sync_config.get('module')
    if not sync_module:
        sys.exit('user_sync module not found!')

    db.init(config['db'])
    spawn(importlib.import_module(sync_module).main, config).join()


if __name__ == '__main__':
    main()
