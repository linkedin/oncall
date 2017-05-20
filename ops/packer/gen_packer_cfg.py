#!/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import print_function

import re
import os
import yaml
import json
import sys

OUTPUT_DIR = 'output'

def main():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    with open('%s/../../src/oncall/__init__.py' % current_dir, 'r') as fd:
        version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                            fd.read(), re.MULTILINE).group(1)

    print('Generating packer config for oncall v%s' % version)
    yml_cfg = sys.argv[1]
    with open(yml_cfg) as fp:
        config = yaml.safe_load(fp)

    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    config['variables']['app_version'] = version
    cfg_name = os.path.splitext(os.path.basename(yml_cfg))[0]
    with open('%s/%s.json' % (OUTPUT_DIR, cfg_name), 'w') as fp:
        json_str = json.dumps(config, indent=2)
        print(json_str)
        fp.write(json_str)

main()
