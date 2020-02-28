# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps as json_dumps


def on_get(req, resp):
    """
    Get all contact modes
    """
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT `name` FROM `contact_mode`')
    data = [row[0] for row in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)
