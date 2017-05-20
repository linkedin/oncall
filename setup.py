#!/usr/bin/env python
# -*- coding:utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import re

with open('src/oncall/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

setup(
    name='oncall',
    version=version,
    packages=['oncall'],
    package_dir={'': 'src'},
    install_requires=[
        'falcon==1.1.0',
        'falcon-cors',
        'gevent',
        'ujson',
        'sqlalchemy',
        'PyYAML',
        'PyMYSQL',
        'phonenumbers',
        'jinja2',
        'streql',
        'webassets',
        'beaker',
        'pycrypto',
        'python-ldap',
        'pytz',
        'irisclient',
        'slackclient',
    ],
    entry_points={
        'console_scripts': [
            'oncall-dev = oncall.bin.run_server:main',
            'oncall-user-sync = oncall.bin.user_sync:main',
            'build_assets = oncall.bin.build_assets:main',
            'oncall-scheduler = oncall.bin.scheduler:main',
            'oncall-notifier = oncall.bin.notifier:main'
        ]
    }
)
