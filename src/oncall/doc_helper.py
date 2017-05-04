# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from oncall.app import init_falcon_api

config = {'auth': {'debug': True, 'module': 'oncall.auth.modules.debug', 'docs': True},
          'debug': True,
          'header_color': '#3a3a3a',
          'healthcheck_path': '/tmp/status',
          'index_content_setting': {'footer': ''},
          'session': {'encrypt_key': 'abc', 'sign_key': '123'}}

app = init_falcon_api(config)  # noqa
