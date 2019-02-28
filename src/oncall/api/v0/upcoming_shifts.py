# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db
from .events import all_columns
from ujson import dumps as json_dumps
from collections import defaultdict
import operator


def on_get(req, resp, user_name):
    '''
    Endpoint for retrieving a user's upcoming shifts. Groups linked events into a single
    entity, with the number of events indicated in the ``num_events`` attribute. Non-linked
    events have ``num_events = 0``. Returns a list of event information for each of that
    user's upcoming shifts. Results can be filtered with the query string params below:

    :query limit: The number of shifts to retrieve. Default is unlimited
    :query role: Filters results to return only shifts with the provided roles.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/users/jdoe/upcoming  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "end": 1496264400,
                "full_name": "John Doe",
                "id": 169877,
                "link_id": "7b3b96279bb24de8ac3fb7dbf06e5d1e",
                "num_events": 7,
                "role": "primary",
                "schedule_id": 1788,
                "start": 1496221200,
                "team": "team-foo",
                "user": "jdoe"
            }
        ]


    '''
    role = req.get_param('role', None)
    limit = req.get_param_as_int('limit')
    query_end = ' ORDER BY `event`.`start` ASC'
    query = '''SELECT %s
               FROM `event`
               JOIN `user` ON `user`.`id` = `event`.`user_id`
               JOIN `team` ON `team`.`id` = `event`.`team_id`
               JOIN `role` ON `role`.`id` = `event`.`role_id`
               WHERE `user`.`id` = (SELECT `id` FROM `user` WHERE `name` = %%s)
                   AND `event`.`start` > UNIX_TIMESTAMP()''' % all_columns

    query_params = [user_name]
    if role:
        query_end = ' AND `role`.`name` = %s' + query_end
        query_params.append(role)
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    cursor.execute(query + query_end, query_params)
    data = cursor.fetchall()
    cursor.close()
    connection.close()
    links = defaultdict(list)
    formatted = []
    for event in data:
        if event['link_id'] is None:
            formatted.append(event)
        else:
            links[event['link_id']].append(event)
    for events in links.values():
        first_event = min(events, key=operator.itemgetter('start'))
        first_event['num_events'] = len(events)
        formatted.append(first_event)
    formatted = sorted(formatted, key=operator.itemgetter('start'))
    if limit is not None:
        formatted = formatted[:limit]
    resp.body = json_dumps(formatted)