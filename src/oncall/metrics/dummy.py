# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import logging
logger = logging.getLogger(__name__)


class dummy(object):
    def __init__(self, config, appname):
        self.appname = appname

    def send_metrics(self, metrics):
        logger.debug('sending metrics: %s', metrics)
