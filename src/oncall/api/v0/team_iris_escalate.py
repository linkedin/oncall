from ... import db, iris
from ...utils import load_json_body
from ...auth import login_required
from falcon import HTTPBadRequest
from requests import ConnectionError


@login_required
def on_post(req, resp, team):
    '''
    Escalate to a team using the team's configured Iris plan. Configured in the
    'iris_plan_integration' section of the configuration file.
    '''
    data = load_json_body(req)

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('SELECT iris_plan FROM team WHERE name = %s', team)
    plan_name = cursor.fetchone()[0]
    cursor.close()
    connection.close()

    requester = req.context.get('user')
    if not requester:
        requester = req.context['app']
    data['requester'] = requester
    if 'description' not in data or data['description'] == '':
        raise HTTPBadRequest('Iris escalation failed', 'Escalation cannot have an empty description')
    if plan_name is None:
        raise HTTPBadRequest('Iris escalation failed', 'No escalation plan specified for team: %s' % team)
    try:
        iris.client.incident(plan_name, context=data)
    except (ValueError, ConnectionError) as e:
        raise HTTPBadRequest('Iris escalation failed', 'Iris client error: %s' % e)
