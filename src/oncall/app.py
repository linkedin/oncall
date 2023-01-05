# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.
from urllib.parse import unquote_plus
from importlib import import_module

import falcon
import os
import re
from beaker.middleware import SessionMiddleware
from falcon_cors import CORS

from . import db, constants, iris, auth

import logging
logger = logging.getLogger('oncall.app')

security_headers = [
    ('X-Frame-Options', 'SAMEORIGIN'),
    ('X-Content-Type-Options', 'nosniff'),
    ('X-XSS-Protection', '1; mode=block'),
    ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
]


def json_error_serializer(req, resp, exception):
    resp.body = exception.to_json()
    resp.content_type = 'application/json'


class SecurityHeaderMiddleware(object):
    def process_request(self, req, resp):
        resp.set_headers(security_headers)


class ReqBodyMiddleware(object):
    '''
    Falcon's req object has a stream that we read to obtain the post body. However, we can only read this once, and
    we often need the post body twice (once for authentication and once in the handler method). To avoid this
    problem, we read the post body into the request context and access it from there.

    IMPORTANT NOTE: Because we use bounded_stream.read() here, all other uses of this method will return '', not the post body.
    '''

    def process_request(self, req, resp):
        req.context['body'] = req.bounded_stream.read()


class AuthMiddleware(object):
    def process_resource(self, req, resp, resource, params):
        try:
            if resource.allow_no_auth:
                return
        except AttributeError:
            pass

        auth_token = req.get_header('AUTHORIZATION')
        if auth_token:
            auth.authenticate_application(auth_token, req)
        else:
            auth.authenticate_user(req)


application = None


def init_falcon_api(config):
    global application
    cors = CORS(allow_origins_list=config.get('allow_origins_list', []))
    middlewares = [
        SecurityHeaderMiddleware(),
        ReqBodyMiddleware(),
        cors.middleware
    ]
    if config.get('require_auth'):
        middlewares.append(AuthMiddleware())
    application = falcon.App(middleware=middlewares)
    application.req_options.auto_parse_form_urlencoded = False
    application.set_error_serializer(json_error_serializer)
    application.req_options.strip_url_path_trailing_slash = True
    from .auth import init as init_auth
    init_auth(application, config['auth'])

    from .ui import init as init_ui
    init_ui(application, config)

    from .api import init as init_api
    init_api(application, config)

    from .healthcheck import init as init_hc
    init_hc(application, config)

    for hook in config.get('post_init_hook', []):
        try:
            logger.debug('loading post init hook <%s>', hook)
            getattr(import_module(hook), 'init')(application, config)
        except:
            logger.exception('Failed loading post init hook <%s>', hook)

    return application


class RawPathPatcher(object):
    slash_re = re.compile(r'%2[Ff]')

    def __init__(self, app):
        self.app = app

    def __call__(self, env, start_response):
        """
        Patch PATH_INFO wsgi variable so that '/api/v0/teams/foo%2Fbar' is not
        treated as '/api/v0/teams/foo/bar'

        List of extensions for raw URI:
            * REQUEST_URI (uwsgi)
            * RAW_URI (gunicorn)
        """
        raw_path = env.get('REQUEST_URI', env.get('RAW_URI')).split('?', 1)[0]
        env['PATH_INFO'] = unquote_plus(self.slash_re.sub('%252F', raw_path))
        return self.app(env, start_response)


def init(config):
    db.init(config['db'])
    constants.init(config)
    if 'iris_plan_integration' in config:
        iris.init(config['iris_plan_integration'])

    if not config.get('debug', False):
        security_headers.append(
            ("Content-Security-Policy",
             # unsafe-eval is required for handlebars without precompiled templates
             "default-src 'self' %s 'unsafe-eval' ; "
             "font-src 'self' data: blob; img-src data: uri https: http:; "
             "style-src 'unsafe-inline' https: http:;" %
             os.environ.get("IRIS_API_HOST", config.get('iris_plan_integration', {}).get('api_host', ''))))
        logging.basicConfig(level=logging.INFO)
        logger.info('%s', security_headers)
    else:
        logging.basicConfig(level=logging.DEBUG)

    init_falcon_api(config)

    global application
    session_opts = {
        'session.type': 'cookie',
        'session.cookie_expires': True,
        'session.key': 'oncall-auth',
        'session.encrypt_key': config['session']['encrypt_key'],
        'session.validate_key': config['session']['sign_key'],
        'session.secure': not (config.get('debug', False) or config.get('allow_http', False)),
        'session.httponly': True,
        'session.crypto_type': 'cryptography'
    }
    application = SessionMiddleware(application, session_opts)
    application = RawPathPatcher(application)


def get_wsgi_app():
    import sys
    from . import utils
    init(utils.read_config(sys.argv[1]))
    return application
