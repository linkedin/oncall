# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTP_204, HTTPBadRequest
from ujson import dumps as json_dumps
from ... import db
from ...auth import login_required, check_user_auth
from ...utils import load_json_body
from .users import get_user_data


writable_columns = {
    'name': '`user`.`name` as `name`',
    'full_name': '`user`.`full_name` as `full_name`',
    'time_zone': '`user`.`time_zone` as `time_zone`',
    'photo_url': '`user`.`photo_url` as `photo_url`',
    'contacts': ('`contact_mode`.`name` AS `mode`, '
                 '`user_contact`.`destination` AS `destination`, '
                 '`user`.`id` AS `contact_id`'),
    'active': '`user`.`active` as `active`'
}


def on_get(req, resp, user_name):
    """
    Get user info by name. Retrieved fields can be filtered with the ``fields``
    query parameter. Valid fields:

    - id - user id
    - name - username
    - contacts - user contact information
    - full_name - user's full name
    - time_zone - user's preferred display timezone
    - photo_url - URL of user's thumbnail photo
    - active - bool indicating whether the user is active in Oncall. Users can
      be marked inactive after leaving the company to preserve past event information.

    If no ``fields`` is provided, the endpoint defaults to returning all fields.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users/jdoe  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

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

    """
    # Format request to filter query on user name
    req.params['name'] = user_name
    data = get_user_data(req.get_param_as_list('fields'), req.params)
    if not data:
        raise HTTPNotFound()
    resp.body = json_dumps(data[0])


@login_required
def on_delete(req, resp, user_name):
    """
    Delete user by name

    **Example request:**

    .. sourcecode:: http

        DELETE /api/v0/users/jdoe HTTP/1.1

    :statuscode 200: Successful delete
    :statuscode 404: User not found
    """
    check_user_auth(user_name, req)
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('DELETE FROM `user` WHERE `name`=%s', user_name)
    connection.commit()
    cursor.close()
    connection.close()


@login_required
def on_put(req, resp, user_name):
    """
    Update user info. Allows edits to:

    - contacts
    - name
    - full_name
    - time_zone
    - photo_url
    - active

    Takes an object specifying the new values of these attributes. ``contacts`` acts
    slightly differently, specifying an object with the contact mode as key and new
    values for that contact mode as values. Any contact mode not specified will be
    unchanged. Similarly, any field not specified in the PUT will be unchanged.

    **Example request:**

    .. sourcecode:: http

        PUT /api/v0/users/jdoe  HTTP/1.1
        Content-Type: application/json

        {
            "contacts": {
                "call": "+1 222-222-2222",
                "email": "jdoe@example2.com"
            }
            "name": "johndoe",
            "full_name": "Johnathan Doe",
        }

    :statuscode 204: Successful edit
    :statuscode 404: User not found
    """
    contacts_query = '''REPLACE INTO user_contact (`user_id`, `mode_id`, `destination`) VALUES
                           ((SELECT `id` FROM `user` WHERE `name` = %(user)s),
                            (SELECT `id` FROM `contact_mode` WHERE `name` = %(mode)s),
                            %(destination)s)
                            '''
    check_user_auth(user_name, req)
    data = load_json_body(req)

    set_contacts = False
    set_columns = []
    for field in data:
        if field == 'contacts':
            set_contacts = True
        elif field in writable_columns:
            set_columns.append('`{0}` = %s'.format(field))
    set_clause = ', '.join(set_columns)

    connection = db.connect()
    cursor = connection.cursor()
    if set_clause:
        query = 'UPDATE `user` SET {0} WHERE `name` = %s'.format(set_clause)
        query_data = []
        for field in data:
            if field != 'contacts':
                query_data.append(data[field])
        query_data.append(user_name)

        cursor.execute(query, query_data)
        if cursor.rowcount != 1:
            cursor.close()
            connection.close()
            raise HTTPBadRequest('No User Found', 'no user exists with given name')

    if set_contacts:
        contacts = []
        for mode, dest in data['contacts'].items():
            contact = {}
            contact['mode'] = mode
            contact['destination'] = dest
            contact['user'] = user_name
            contacts.append(contact)
        cursor.executemany(contacts_query, contacts)
    connection.commit()
    cursor.close()
    connection.close()
    resp.status = HTTP_204
