# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ... import db, iris
from ...utils import load_json_body
from ...auth import login_required
from ...constants import URGENT, MEDIUM, CUSTOM
from falcon import HTTPBadRequest
from requests import ConnectionError, HTTPError


@login_required
def on_post(req, resp, team):
    '''
    Escalate to a team using Iris. Configured in the 'iris_plan_integration' section of
    the configuration file. Escalation plan is specified via keyword, currently: 'urgent',
    'medium', or 'custom'. These keywords correspond to the plan specified in the
    iris_plan_integration urgent_plan key, the iris integration medium_plan key, and the team's
    iris plan defined in the DB, respectively. If no plan is specified, the team's custom plan will be
    used. If iris plan integration is not activated, this endpoint will be disabled.

    **Example request:**

    .. sourcecode:: http

        POST /v0/events   HTTP/1.1
        Content-Type: application/json

        {
            "description": "Something bad happened!",
            "plan": "urgent"
        }

    :statuscode 200: Incident created
    :statuscode 400: Escalation failed, missing description/No escalation plan specified
    for team/Iris client error.
    '''
    data = load_json_body(req)

    plan = data.get('plan')
    dynamic = False
    if plan == URGENT:
        plan_settings = iris.settings['urgent_plan']
        dynamic = True
    elif plan == MEDIUM:
        plan_settings = iris.settings['medium_plan']
        dynamic = True
    elif plan == CUSTOM or plan is None:
        # Default to team's custom plan for backwards compatibility
        connection = db.connect()
        cursor = connection.cursor()
        cursor.execute('SELECT iris_plan FROM team WHERE name = %s', team)
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            raise HTTPBadRequest('Iris escalation failed', 'No escalation plan specified '
                                                           'and team has no custom escalation plan defined')
        plan_name = cursor.fetchone()[0]
        cursor.close()
        connection.close()
    else:
        raise HTTPBadRequest('Iris escalation failed', 'Invalid escalation plan')

    requester = req.context.get('user')
    if not requester:
        requester = req.context['app']
    data['requester'] = requester
    if 'description' not in data or data['description'] == '':
        raise HTTPBadRequest('Iris escalation failed', 'Escalation cannot have an empty description')
    try:
        if dynamic:
            plan_name = plan_settings['name']
            targets = plan_settings['dynamic_targets']
            for t in targets:
                # Set target to team name if not overridden in settings
                if 'target' not in t:
                    t['target'] = team
            re = iris.client.post(iris.client.url + 'incidents',
                                  json={'plan': plan_name, 'context': data, 'dynamic_targets': targets})
            re.raise_for_status()
            incident_id = re.json()
        else:
            incident_id = iris.client.incident(plan_name, context=data)
    except (ValueError, ConnectionError, HTTPError) as e:
        raise HTTPBadRequest('Iris escalation failed', 'Iris client error: %s' % e)

    resp.body = str(incident_id)
