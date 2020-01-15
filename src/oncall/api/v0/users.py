# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPError, HTTPBadRequest, HTTP_201
from ujson import dumps as json_dumps
from ... import db
from ... import auth
from ...utils import load_json_body


JOIN_CONTACT_TABLES = (' LEFT JOIN `user_contact` ON `user`.`id` = `user_contact`.`user_id`'
                       ' LEFT JOIN `contact_mode` ON `user_contact`.`mode_id` = `contact_mode`.`id`')

columns = {
    'id': '`user`.`id` as `id`',
    'name': '`user`.`name` as `name`',
    'full_name': '`user`.`full_name` as `full_name`',
    'time_zone': '`user`.`time_zone` as `time_zone`',
    'photo_url': '`user`.`photo_url` as `photo_url`',
    'contacts': ('`contact_mode`.`name` AS `mode`, '
                 '`user_contact`.`destination` AS `destination`, '
                 '`user`.`id` AS `contact_id`'),
    'active': '`user`.`active` as `active`',
    'god': '`user`.`god` as `god`',
}

all_columns = ', '.join(columns.values())

constraints = {
    'id': '`user`.`id` = %s',
    'id__eq': '`user`.`id` = %s',
    'id__ne': '`user`.`id` != %s',
    'id__lt': '`user`.`id` < %s',
    'id__le': '`user`.`id` <= %s',
    'id__gt': '`user`.`id` > %s',
    'id__ge': '`user`.`id` >= %s',
    'name': '`user`.`name` = %s',
    'name__eq': '`user`.`name` = %s',
    'name__contains': '`user`.`name` LIKE CONCAT("%%", %s, "%%")',
    'name__startswith': '`user`.`name` LIKE CONCAT(%s, "%%")',
    'name__endswith': '`user`.`name` LIKE CONCAT("%%", %s)',
    'full_name': '`user`.`full_name` = %s',
    'full_name__eq': '`user`.`full_name` = %s',
    'full_name__contains': '`user`.`full_name` LIKE CONCAT("%%", %s, "%%")',
    'full_name__startswith': '`user`.`full_name` LIKE CONCAT(%s, "%%")',
    'full_name__endswith': '`user`.`full_name` LIKE CONCAT("%%", %s)',
    'active': '`user`.`active` = %s'
}


def get_user_data(fields, filter_params, dbinfo=None):
    """
    Get user data for a request
    """
    contacts = False
    from_clause = '`user`'

    if fields:
        if 'contacts' in fields:
            from_clause += JOIN_CONTACT_TABLES
            contacts = True

        if any(f not in columns for f in fields):
            raise HTTPBadRequest('Bad fields', 'One or more invalid fields')

        fields = map(columns.__getitem__, fields)
        cols = ', '.join(fields)
    else:
        from_clause += JOIN_CONTACT_TABLES
        cols = all_columns
        contacts = True

    connection_opened = False
    if dbinfo is None:
        connection = db.connect()
        connection_opened = True
        cursor = connection.cursor(db.DictCursor)
    else:
        connection, cursor = dbinfo

    where = ' AND '.join(constraints[key] % connection.escape(value)
                         for key, value in filter_params.items()
                         if key in constraints)
    query = 'SELECT %s FROM %s' % (cols, from_clause)
    if where:
        query = '%s WHERE %s' % (query, where)

    cursor.execute(query)
    data = cursor.fetchall()
    if connection_opened:
        cursor.close()
        connection.close()

    # Format contact info
    if contacts:
        # end result accumulator
        ret = {}
        for row in data:
            user_id = row.pop('contact_id')
            # add data row into accumulator only if not already there
            if user_id not in ret:
                ret[user_id] = row
                ret[user_id]['contacts'] = {}
            mode = row.pop('mode')
            if not mode:
                continue
            dest = row.pop('destination')
            ret[user_id]['contacts'][mode] = dest
        data = list(ret.values())
    return data


def on_get(req, resp):
    """
    Get users filtered by params. Returns a list of user info objects for all users matching
    filter parameters.

    :query id: id of the user
    :query id__eq: id of the user
    :query id__gt: id greater than
    :query id__ge: id greater than or equal
    :query id__lt: id less than
    :query id__le: id less than or equal
    :query name: username
    :query name__eq: username
    :query name__contains: username contains param
    :query name__startswith: username starts with param
    :query name__endswith: username ends with param
    :query full_name: full name
    :query full_name__eq: username
    :query full_name__contains: full name contains param
    :query full_name__startswith: full name starts with param
    :query full_name__endswith: full name ends with param
    :query active: whether user has been deactivated (deleted)


    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users?name=jdoe   HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "active": 1,
                "contacts": {
                    "call": "+1 111-111-1111",
                    "email": "jdoe@example.com",
                    "im": "jdoe",
                    "sms": "+1 111-111-1111"
                },
                "full_name": "John Doe",
                "id": 1234,
                "name": "jdoe",
                "photo_url": "image.example.com",
                "time_zone": "US/Pacific"
            }
        ]

    """
    resp.body = json_dumps(get_user_data(req.get_param_as_list('fields'), req.params))


@auth.debug_only
def on_post(req, resp):
    """
    Create user. Currently used only in debug mode.
    """
    data = load_json_body(req)
    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO `user` (`name`) VALUES (%(name)s)', data)
        connection.commit()
    except db.IntegrityError:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'user name "%(name)s" already exists' % data)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
