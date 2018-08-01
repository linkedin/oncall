# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from ujson import dumps


def on_get(req, resp):
    '''
    Endpoint for searching for teams, services, users, and team users by keyword. Used for
    typeaheads in the frontend. Team/service search is done using substring matching, while
    user and team_user search is done with prefix matching. If no fields are provided, the
    endpoint defaults to ['teams', 'services']. A keyword parameter must be passed in the
    query string.

    **Example request**

    .. sourcecode:: http

        GET /api/v0/search?keyword=key  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

            {
                "services": [
                        {
                            "service-key": "team-foo"
                        },
                        {
                            "service-key2": "team-bar"
                        }
                    ]
                "teams": [
                        "team-key",
                        "team-key2"
                    ]
            }

    An example for user search:
    **Example request**

    .. sourcecode:: http

        GET /api/v0/search?keyword=key&fields=users  HTTP/1.1
        Host: example.com


    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "users":
                [
                    {
                        "full_name": "John Doe",
                        "name": "jdoe"
                    }
                ]
        }

    '''
    keyword = req.get_param('keyword', required=True)
    fields = req.get_param_as_list('fields')
    if not fields:
        fields = ['teams', 'services', 'users']

    connection = db.connect()
    cursor = connection.cursor()

    data = {}
    if 'teams' in fields:
        query = 'SELECT `name` FROM `team` WHERE `team`.`name` LIKE CONCAT("%%", %s, "%%") ' \
                'AND `active` = TRUE'
        cursor.execute(query, keyword)
        data['teams'] = [r[0] for r in cursor]

    if 'services' in fields:
        query = '''SELECT `service`.`name` as `service`, `team`.`name` as `team` FROM `service`
                JOIN `team_service` ON `service`.`id` = `team_service`.`service_id`
                JOIN `team` ON `team`.`id` = `team_service`.`team_id`
                WHERE `service`.`name` LIKE CONCAT("%%", %s, "%%") AND `team`.`active` = TRUE'''
        cursor.execute(query, keyword)
        services = {}
        for row in cursor:
            serv, team = row
            if serv in services:
                services[serv].append(team)
            else:
                services[serv] = [team]
        data['services'] = services

    if 'users' in fields:
        query = '''SELECT  `full_name`, `name` FROM `user`
                   WHERE `active` = TRUE AND (`name` LIKE CONCAT(%s, "%%") OR `full_name` LIKE CONCAT(%s, "%%"))'''
        cursor.execute(query, (keyword, keyword))
        data['users'] = [{'full_name': r[0], 'name': r[1]} for r in cursor]

    if 'team_users' in fields:
        filter = '%s%%' % keyword
        team = req.get_param('team', required=True)
        query = '''SELECT `user`.`full_name`, `user`.`name`
                   FROM `team_user` JOIN `user` ON `team_user`.`user_id` = `user`.`id`
                   WHERE `team_user`.`team_id` = (SELECT `id` FROM `team` WHERE `name` = %s)
                   AND (`name` LIKE %s OR `full_name` LIKE %s)'''
        cursor.execute(query, (team, filter, filter))
        data['users'] = [{'full_name': r[0], 'name': r[1]} for r in cursor]

    cursor.close()
    connection.close()
    resp.body = dumps(data)
