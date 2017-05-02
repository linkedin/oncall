# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTP_204, HTTPBadRequest
from ujson import dumps as json_dumps
from ... import db
from ...auth import login_required, check_user_auth
from ...utils import load_json_body
from .users import columns, get_user_data


def on_get(req, resp, user_name):
    """
    Get user info by name
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
    Update user info
    """
    contacts_query = '''INSERT INTO user_contact (`user_id`, `mode_id`, `destination`) VALUES
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
        elif field in columns:
            set_columns.append('`{0}` = %s'.format(field))
    set_clause = ', '.join(set_columns)

    connection = db.connect()
    cursor = connection.cursor()
    if set_clause:
        query = 'UPDATE `user` SET {0} WHERE `name` = %s'.format(set_clause)
        query_data = tuple(data[field] for field in data) + (user_name,)

        cursor.execute(query, query_data)
        if cursor.rowcount != 1:
            cursor.close()
            connection.close()
            raise HTTPBadRequest('No User Found', 'no user exists with given name')

    if set_contacts:
        contacts = []
        for mode, dest in data['contacts'].iteritems():
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
