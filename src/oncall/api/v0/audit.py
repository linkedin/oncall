# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps
from ... import db


filters = {'owner': '`owner_name` = %(owner)s',
           'team': '`team_name` = %(team)s',
           'action': '`action_name` IN %(action)s',
           'start': '`timestamp` >= %(start)s',
           'end': '`timestamp` <= %(end)s'}


def on_get(req, resp):
    '''
    Search audit log. Allows filtering based on a number of parameters,
    detailed below. Returns an entry in the audit log, including the name
    of the associated team, action owner, and action type, as well as a
    timestamp and the action context. The context tracks different data
    based on the action, which may be useful in investigating.
    Audit logs are tracked for the following actions:

    * admin_created
    * event_created
    * event_edited
    * roster_created
    * roster_edited
    * roster_user_added
    * roster_user_deleted
    * team_created
    * team_edited
    * event_deleted
    * event_swapped
    * roster_user_edited
    * team_deleted
    * admin_deleted
    * roster_deleted
    * event_substituted


    **Example request**:

    .. sourcecode:: http

       GET /api/v0/audit?team=foo-sre&end=1487466146&action=event_created  HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "context":"{"new_event_id":441072,"request_body":{"start":1518422400,"end":1518595200,"role":"primary","user":jdoe","team":"foo-sre"}}"
                "timestamp": 1488441600,
                "team_name": "foo-sre",
                "owner_name": "jdoe"
                "action_name: "event_created"
            }
        ]

    :query team: team name
    :query owner: action owner name
    :query action: name of action taken. If provided multiple action names,
    :query id: id of the event
    :query start: lower bound for audit entry's timestamp (unix timestamp)
    :query end: upper bound for audit entry's timestamp (unix timestamp)
    '''
    connection = db.connect()
    cursor = connection.cursor(db.DictCursor)
    if 'action' in req.params:
        req.params['action'] = req.get_param_as_list('action')

    query = '''SELECT `owner_name` AS `owner`, `team_name` AS `team`,
                   `action_name` AS `action`, `timestamp`, `context`
               FROM `audit`'''
    where = ' AND '.join(filters[field] for field in req.params if field in filters)
    if where:
        query = '%s WHERE %s' % (query, where)

    cursor.execute(query, req.params)
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    resp.body = json_dumps(results)