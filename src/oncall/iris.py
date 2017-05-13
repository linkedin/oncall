# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from irisclient import IrisClient

client = None
settings = None


def init(config):
    global client
    global settings
    settings = {key: config[key] for key in config if key != 'api_key'}
    client = IrisClient(config['app'], config['api_key'], config['api_host'])