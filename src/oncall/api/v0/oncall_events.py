# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import json
import os
import yaml
from linkedin.environment import application_environment
from .events import on_get as get_events
from collections import defaultdict
import requests
from ujson import dumps as json_dumps
from falcon import HTTPBadRequest

constraints = {
    'id': '`event`.`id` = %s',
    'id__eq': '`event`.`id` = %s',
    'id__ne': '`event`.`id` != %s',
    'id__gt': '`event`.`id` > %s',
    'id__ge': '`event`.`id` >= %s',
    'id__lt': '`event`.`id` < %s',
    'id__le': '`event`.`id` <= %s',
    'start': '`event`.`start` = %s',
    'start__eq': '`event`.`start` = %s',
    'start__ne': '`event`.`start` != %s',
    'start__gt': '`event`.`start` > %s',
    'start__ge': '`event`.`start` >= %s',
    'start__lt': '`event`.`start` < %s',
    'start__le': '`event`.`start` <= %s',
    'end': '`event`.`end` = %s',
    'end__eq': '`event`.`end` = %s',
    'end__ne': '`event`.`end` != %s',
    'end__gt': '`event`.`end` > %s',
    'end__ge': '`event`.`end` >= %s',
    'end__lt': '`event`.`end` < %s',
    'end__le': '`event`.`end` <= %s',
    'role': '`role`.`name` = %s',
    'role__eq': '`role`.`name` = %s',
    'role__contains': '`role`.`name` LIKE CONCAT("%%", %s, "%%")',
    'role__startswith': '`role`.`name` LIKE CONCAT(%s, "%%")',
    'role__endswith': '`role`.`name` LIKE CONCAT("%%", %s)',
    'team': '`team`.`name` = %s',
    'team__eq': '`team`.`name` = %s',
    'team__contains': '`team`.`name` LIKE CONCAT("%%", %s, "%%")',
    'team__startswith': '`team`.`name` LIKE CONCAT(%s, "%%")',
    'team__endswith': '`team`.`name` LIKE CONCAT("%%", %s)',
    'team_id': '`team`.`id` = %s',
    'user': '`user`.`name` = %s',
    'user__eq': '`user`.`name` = %s',
    'user__contains': '`user`.`name` LIKE CONCAT("%%", %s, "%%")',
    'user__startswith': '`user`.`name` LIKE CONCAT(%s, "%%")',
    'user__endswith': '`user`.`name` LIKE CONCAT("%%", %s)'
}


def on_get(req, resp):
    """
    Search for events. Allows filtering based on a number of parameters,
    detailed below. Also returns only the users who are paid to be on call. Uses response from
    http://oncall-bonus.prod.linkedin.com/bonus/api/v0/teams/{team} to identify paid status.

    **Example request**:

    .. sourcecode:: http

       GET /api/v0/oncall_events?team=foo-sre&end__gt=1487466146&role=primary HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "ldap_user_id":
                [
                    {
                        "start": 1488441600,
                        "end": 1489132800,
                        "team": "foo-sre",
                        "link_id": null,
                        "schedule_id": null,
                        "role": "primary",
                        "user": "foo",
                        "full_name": "Foo Icecream",
                        "id": 187795
                    },
                    {
                        "start": 1488441600,
                        "end": 1489132800,
                        "team": "foo-sre",
                        "link_id": "8a8ae77b8c52448db60c8a701e7bffc2",
                        "schedule_id": 123,
                        "role": "primary",
                        "user": "bar",
                        "full_name": "Bar Apple",
                        "id": 187795
                    }
                ]
        ]

    :query team: team name
    :query user: user name
    :query role: role name
    :query id: id of the event
    :query start: start time (unix timestamp) of event
    :query end: end time (unix timestamp) of event
    :query start__gt: start time (unix timestamp) greater than
    :query start__ge: start time (unix timestamp) greater than or equal
    :query start__lt: start time (unix timestamp) less than
    :query start__le: start time (unix timestamp) less than or equal
    :query end__gt: end time (unix timestamp) greater than
    :query end__ge: end time (unix timestamp) greater than or equal
    :query end__lt: end time (unix timestamp) less than
    :query end__le: end time (unix timestamp) less than or equal
    :query role__eq: role name
    :query role__contains: role name contains param
    :query role__startswith: role name starts with param
    :query role__endswith: role name ends with param
    :query team__eq: team name
    :query team__contains: team name contains param
    :query team__startswith: team name starts with param
    :query team__endswith: team name ends with param
    :query team_id: team id
    :query user__eq: user name
    :query user__contains: user name contains param
    :query user__startswith: user name starts with param
    :query user__endswith: user name ends with param

    :statuscode 200: no error
    :statuscode 400: bad request
    """
    req.params.pop('fields', None)
    req.params.pop('include_subscribed', None)
    if any(key not in constraints for key in req.params):
        raise HTTPBadRequest('Bad constraint param')
    get_events(req, resp)
    env = application_environment()
    config_file_path = os.path.join(env.config_path, 'oncall-api.yaml')
    with open(config_file_path) as f:
        config = yaml.safe_load(f)
    oncall_blacklist = set(config.get('oncall_blacklist', []))
    oncall_whitelist = set(config.get('oncall_whitelist', []))
    ldap_grouping = defaultdict(list)
    user_bonus_status = {}
    for event in json.loads(resp.body):
        if event['role'].lower() == 'manager':
            continue
        team = event['team']
        if team in oncall_whitelist:
            ldap_grouping[event['user']].append(event)
            continue
        if team in oncall_blacklist:
            continue
        if team not in user_bonus_status:
            bonus_url = "http://oncall-bonus.prod.linkedin.com/bonus/api/v0/teams/" + team
            try:
                team_payment_details = requests.get(bonus_url).json()
            except:
                team_payment_details = {
                    'primary_paid': 0,
                    'secondary_paid': 0
                }
            user_bonus_status[team] = {'primary': team_payment_details.get('primary_paid', 0), 'secondary': team_payment_details.get('secondary_paid', 0)}
        paid = user_bonus_status[team].get(event['role'], 0)
        if not paid:
            continue
        ldap_grouping[event['user']].append(event)
    resp.body = json_dumps(ldap_grouping)
