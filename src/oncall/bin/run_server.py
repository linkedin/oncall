#!/usr/bin/env python

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import gc
import sys
import multiprocessing
import gunicorn.app.base
import oncall.utils
import importlib


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, options=None, skip_build_assets=False):
        self.options = options or {}
        self.skip_build_assets = skip_build_assets
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        import oncall
        importlib.reload(oncall.utils)

        import oncall.app
        app = oncall.app.get_wsgi_app()

        if not self.skip_build_assets:
            for r in gc.get_referrers(self):
                if isinstance(r, dict) and '_num_workers' in r:
                    gunicorn_arbiter = r

            # only build assets on one worker to avoid race conditions
            if gunicorn_arbiter['worker_age'] % self.options['workers'] == 0:
                import oncall.ui
                oncall.ui.build_assets()

        return app


def main():
    if len(sys.argv) <= 1:
        sys.exit('USAGE: %s CONFIG_FILE [--skip-build-assets]' % sys.argv[0])
    elif len(sys.argv) >= 3:
        skip_build_assets = (sys.argv[2] == '--skip-build-assets')
    else:
        skip_build_assets = False

    config = oncall.utils.read_config(sys.argv[1])
    server = config['server']

    options = {
        'preload_app': False,
        'reload': True,
        'bind': '%s:%s' % (server['host'], server['port']),
        'worker_class': 'gevent',
        'accesslog': '-',
        'workers': multiprocessing.cpu_count()
    }

    gunicorn_server = StandaloneApplication(options, skip_build_assets)
    gunicorn_server.run()


if __name__ == '__main__':
    main()
