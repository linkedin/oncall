# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
import json
import time
from .events import on_get as get_events
from collections import defaultdict
import requests
from ujson import dumps as json_dumps
from falcon import HTTPStatus, HTTP_200


class PaidEvents(object):
    def __init__(self, config):
        self.config = config

    def on_get(self, req, resp):
        """
        Search for events. Allows filtering based on a number of parameters,
        detailed below. Also returns only the users who are paid to be on call. Uses response from
        oncall-bonus to identify paid status.

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

        config = self.config
        oncall_bonus_blacklist = config.get('bonus_blacklist', [])
        oncall_bonus_whitelist = config.get('bonus_whitelist', [])
        bonus_url = config.get('bonus_url', None)
        ldap_grouping = defaultdict(list)

        # if start time is not specified only fetch events in the future
        if not req.params.get('start__gt'):
            req.params['start__gt'] = str(int(time.time()))

        get_events(req, resp)

        # fetch team data from an externall oncall-bonus api
        try:
            bonus_response = requests.get(bonus_url)
            bonus_response.raise_for_status()
        except requests.exceptions.RequestException:
            raise HTTPStatus('503 failed to contact oncall-bonus API')

        oncall_bonus_teams = bonus_response.json()

        for event in json.loads(resp.body):
            if event['role'].lower() == 'manager':
                continue

            team = event['team']
            if team in oncall_bonus_whitelist:
                ldap_grouping[event['user']].append(event)
                continue
            if team in oncall_bonus_blacklist:
                continue

            # check if event's role is payed for that team
            team_payment_details = next((item for item in oncall_bonus_teams if item.get('name', '') == team), None)
            if team_payment_details:
                team_payed_roles = {'primary': team_payment_details.get('primary_paid', 0), 'secondary': team_payment_details.get('secondary_paid', 0)}
                if team_payed_roles.get(event['role']):
                    ldap_grouping[event['user']].append(event)

        resp.status = HTTP_200
        resp.body = json_dumps(ldap_grouping)
