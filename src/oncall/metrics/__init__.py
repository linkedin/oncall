# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from oncall.utils import import_custom_module
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

stats_reset = {}

# defaultdict so stats updates don't break if metrics haven't been initialized
stats = defaultdict(int)

metrics_provider = None
custom_metrics_senders = []


def get_metrics_provider(config, app_name):
    return import_custom_module('oncall.metrics',
                                config['metrics'])(config, app_name)

def fill_custom_exporters(config):
    for i in config['custom-exporters']['exporters']:
        custom_metrics_senders.append(
            import_custom_module('oncall.metrics', i['name'])(i['server_port'], config['custom-exporters']['app-name']))


def emit_metrics():
    if metrics_provider:
        metrics_provider.send_metrics(stats)
    stats.update(stats_reset)

    for i in custom_metrics_senders:
        i.update_metrics()


def init(config, app_name, default_stats):
    global metrics_provider
    metrics_provider = get_metrics_provider(config, app_name)
    logger.info('Loaded metrics handler %s', config['metrics'])
    stats_reset.update(default_stats)
    stats.update(stats_reset)
    fill_custom_exporters(config)
