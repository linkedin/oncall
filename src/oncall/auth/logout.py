# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from .. import db


def on_post(req, resp):
    session = req.env['beaker.session']
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('DELETE FROM `session` WHERE `id` = %s', session['_id'])
    connection.commit()
    cursor.close()
    connection.close()

    session.delete()
