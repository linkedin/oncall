# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.


class Authenticator(object):
    def __init__(self, config=None):
        pass

    def authenticate(self, request):
        # DUMMY SSO AUTHENTICATION FOR TEST USE ONLY, DO NOT USE IN PRODUCTION! Replace with your own SSO authentication module.
        if 'SSO-DEBUG-HEADER' in request.headers:
            return request.headers.get('SSO-DEBUG-HEADER')
        return None
