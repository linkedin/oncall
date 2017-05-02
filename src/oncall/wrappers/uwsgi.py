# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from __future__ import absolute_import


def bootstrap():
    import uwsgi
    import os

    uwsgi.lock()
    min_pid = min([w['pid'] for w in uwsgi.workers()])
    if min_pid == os.getpid():
        from oncall.ui import build
        print 'building webassets...'
        build()
    uwsgi.unlock()
