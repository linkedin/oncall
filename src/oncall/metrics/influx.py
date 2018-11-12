# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

# This is named 'influx' to avoid conflicting with the influxdb module

from datetime import datetime
import logging
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import RequestException

logger = logging.getLogger()


# pip install influxdb==3.0.0
class influx(object):
    def __init__(self, config, appname):
        try:
            self.client = InfluxDBClient(**config['influxdb']['connect'])
            self.enable_metrics = True
        except KeyError:
            logger.warning('Missing connect arguments for influxdb. Running with no metrics.')
            self.enable_metrics = False
            return
        try:
            self.extra_tags = config['influxdb']['tags']
        except KeyError:
            self.extra_tags = {}
        self.appname = appname

    def send_metrics(self, metrics):
        if not self.enable_metrics:
            return
        now = str(datetime.now())
        payload = []
        for metric, value in metrics.items():
            data = {
                'measurement': self.appname,
                'tags': {},
                'time': now,
                'fields': {
                    metric: value
                }
            }
            if self.extra_tags:
                data['tags'].update(self.extra_tags)
            payload.append(data)

        try:
            self.client.write_points(payload)
        except (RequestException, InfluxDBClientError, InfluxDBServerError):
            logger.exception('Failed to send metrics to influxdb')
