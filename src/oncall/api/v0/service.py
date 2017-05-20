# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound
from ujson import dumps
from ...utils import load_json_body

from ... import db
from ...auth import debug_only


def on_get(req, resp, service):
    """
    Get service id by name

    **Example request**

    .. sourcecode:: http

        GET /api/v0/services/service-foo  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "id": 1234,
            "name": "service-foo"
        }

    """
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute('SELECT `id`, `name` FROM `service` WHERE `name`=%s', service)
    results = cursor.fetchall()
    if not results:
        raise HTTPNotFound()
    [service] = results
    cursor.close()
    connection.close()
    resp.body = dumps(service)


@debug_only
def on_put(req, resp, service):
    """
    Change name for a service. Currently unused/debug only.
    """
    data = load_json_body(req)
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('UPDATE `service` SET `name`=%s WHERE `name`=%s',
                   (data['name'], service))
    connection.commit()
    cursor.close()
    connection.close()


@debug_only
def on_delete(req, resp, service):
    """
    Delete a service. Currently unused/debug only.
    """
    connection = db.connect()
    cursor = connection.cursor()

    # FIXME: also delete team service mappings?
    cursor.execute('DELETE FROM `service` WHERE `name`=%s', service)
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()

    if deleted == 0:
        raise HTTPNotFound()
