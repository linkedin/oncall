import psutil
from prometheus_client import start_http_server, Gauge, CollectorRegistry
import logging


logger = logging.getLogger()

class custom_exporter(object):
    def __init__(self, server_port, appname):
        registry = CollectorRegistry()

        try:
            port = int(server_port)
        except (ValueError, KeyError):
            logger.warning('custom_exporter server_port not present in config. running without metrics.')
            self.enable_metrics = False
            return

        self.memory_usage = Gauge(f'{appname}_memory_ratio', 'Memory usage in percents.', registry=registry)
        self.cpu_usage = Gauge(f'{appname}_cpu_ratio', 'CPU usage in percents.', registry=registry)

        logger.info('Starting custom exporter web server at %s', port)
        start_http_server(port, registry=registry)
        self.enable_metrics = True

    def update_metrics(self):
        if self.enable_metrics:
            self.memory_usage.set(psutil.virtual_memory().percent / 100)
            self.cpu_usage.set(psutil.cpu_percent() / 100)
