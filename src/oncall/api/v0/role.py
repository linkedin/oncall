# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound
from ... import db
from ...auth import debug_only


@debug_only
def on_delete(req, resp, role):
    connection = db.connect()
    cursor = connection.cursor()
    # TODO: also remove any schedule and event that references the role?
    cursor.execute('DELETE FROM `role` WHERE `name`=%s', role)
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()

    if deleted == 0:
        raise HTTPNotFound()
