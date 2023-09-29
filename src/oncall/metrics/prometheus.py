# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import os

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from prometheus_client import Gauge, start_http_server, CollectorRegistry, write_to_textfile
import re
import logging

logger = logging.getLogger()


# pip install prometheus_client
# Docs at https://github.com/prometheus/client_python
class prometheus(object):
    def __init__(self, config, appname):
        try:
            port = int(config['prometheus'][appname]['server_port'])
        except (ValueError, KeyError):
            logger.warning('prometheus server_port not present in config. running without metrics.')
            self.enable_metrics = False
            return

        self.gauges = {}

        # per docs, app name in metric prefix needs to be one word
        self.appname = re.sub('[^a-zA-Z0-9]+', '', appname)

        logger.info('Starting prometheus metrics web server at %s', port)
        start_http_server(port)
        self.enable_metrics = True

    def send_metrics(self, metrics):
        if not self.enable_metrics:
            return
        for metric, value in metrics.items():
            if metric not in self.gauges:
                self.gauges[metric] = Gauge(self.appname + '_' + metric, '')
            logger.info('Setting metrics gauge %s to %s', metric, value)
            self.gauges[metric].set_to_current_time()
            self.gauges[metric].set(value)

        self._send_custom_metrics()

    def _send_custom_metrics(self):
        registry = CollectorRegistry()

        self.get_files_amount(
            registry,
            "/home/oncall/var/log/uwsgi",
            "uwsgi_logs_amount",
            "Amount of uwsgi log files."
        )
        self.get_files_amount(
            registry,
            "/home/oncall/var/log/nginx",
            "nginx_logs_amount",
            "Amount of nginx log files."
        )

        write_to_textfile('/home/oncall/node-exporter/textfile-collector/metrics.prom', registry)

    @staticmethod
    def get_files_amount(registry, path, metrics_name, metrics_description):
        g = Gauge(metrics_name, metrics_description, registry=registry)
        amount = str(len([name for name in os.listdir(path)]))
        g.set(amount)
