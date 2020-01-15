# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPNotFound, HTTPUnauthorized, HTTPBadRequest
from falcon.util import uri
from oncall.api.v0.users import get_user_data
from ujson import dumps
from oncall import db
from random import SystemRandom
from . import auth_manager

allow_no_auth = True


def on_post(req, resp):
    login_info = uri.parse_query_string(req.context['body'].decode('utf-8'))

    user = login_info.get('username')
    password = login_info.get('password')
    if user is None or password is None:
        raise HTTPBadRequest('Invalid login attempt', 'Missing user/password')

    if not auth_manager.authenticate(user, password):
        raise HTTPUnauthorized('Authentication failure', 'bad login credentials', '')

    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    data = get_user_data(None, {'name': user}, dbinfo=(connection, cursor))
    if not data:
        cursor.close()
        connection.close()
        raise HTTPNotFound()

    session = req.env['beaker.session']
    session['user'] = user
    session.save()
    csrf_token = '%x' % SystemRandom().getrandbits(128)
    try:
        cursor.execute('INSERT INTO `session` (`id`, `csrf_token`) VALUES (%s, %s)',
                       (req.env['beaker.session']['_id'], csrf_token))
    except db.IntegrityError:
        raise HTTPBadRequest('Invalid login attempt', 'User already logged in')
    connection.commit()
    cursor.close()
    connection.close()

    # TODO: purge out of date csrf token
    data[0]['csrf_token'] = csrf_token
    resp.body = dumps(data[0])
