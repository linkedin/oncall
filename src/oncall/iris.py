# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

try:
    from irisclient import IrisClient
except ImportError:
    IrisClient = None


client = None
settings = None


def init(config):
    global client
    global settings
    if IrisClient:
        settings = {key: config[key] for key in config if key != 'api_key'}
        client = IrisClient(config['app'], config['api_key'], config['api_host'])
