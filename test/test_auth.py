from oncall.auth import login_required
from oncall.app import ReqBodyMiddleware
import falcon
import falcon.testing
import time
import hmac
import hashlib
import base64


class DummyAPI(object):

    @login_required
    def on_get(self, req, resp):
        resp.content = 'GOOD'

    @login_required
    def on_post(self, req, resp):
        resp.status = falcon.HTTP_201


def test_application_auth(mocker):
    # Mock DB to get 'abc' as the dummy app key
    connect = mocker.MagicMock(name='dummyDB')
    cursor = mocker.MagicMock(name='dummyCursor', rowcount=1)
    cursor.fetchone.return_value = ['abc']
    connect.cursor.return_value = cursor
    db = mocker.MagicMock()
    db.connect.return_value = connect
    mocker.patch('oncall.auth.db', db)

    # Set up dummy API for auth testing
    api = falcon.API(middleware=[ReqBodyMiddleware()])
    api.add_route('/dummy_path', DummyAPI())

    # Test bad auth
    client = falcon.testing.TestClient(api)
    re = client.simulate_get('/dummy_path', headers={'AUTHORIZATION': 'hmac dummy:abc'})
    assert re.status_code == 401
    re = client.simulate_post('/dummy_path', json={'example': 'test'}, headers={'AUTHORIZATION': 'hmac dummy:abc'})
    assert re.status_code == 401

    # Test good auth for GET request
    window = int(time.time()) // 5
    text = '%s %s %s %s' % (window, 'GET', '/dummy_path?abc=123', '')
    HMAC = hmac.new(b'abc', text.encode('utf-8'), hashlib.sha512)
    digest = base64.urlsafe_b64encode(HMAC.digest()).decode('utf-8')
    auth = 'hmac dummy:%s' % digest

    re = client.simulate_get('/dummy_path', params={'abc': 123}, headers={'AUTHORIZATION': auth})
    assert re.status_code == 200

    window = int(time.time()) // 5
    body = '{"example": "test"}'
    text = '%s %s %s %s' % (window, 'POST', '/dummy_path', body)
    HMAC = hmac.new(b'abc', text.encode('utf-8'), hashlib.sha512)
    digest = base64.urlsafe_b64encode(HMAC.digest()).decode('utf-8')
    auth = 'hmac dummy:%s' % digest

    re = client.simulate_post('/dummy_path', body=body, headers={'AUTHORIZATION': auth})
    assert re.status_code == 201