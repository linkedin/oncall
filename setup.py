#!/usr/bin/env python
# -*- coding:utf-8 -*-

import setuptools
import re

with open('src/oncall/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

setuptools.setup(
    name='oncall',
    version=version,
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    include_package_data=True,
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
        'cryptography==2.3',
        'python-ldap',
        'pytz',
        'irisclient',
        'slackclient',
        'icalendar',
        'pymsteams'
    ],
    extras_require={
        'ldap': ['python-ldap'],
        'prometheus': ['prometheus_client'],
        'dev': [
            'pytest',
            'pytest-mock',
            'requests',
            'gunicorn',
            'flake8',
            'Sphinx==1.5.6',
            'sphinxcontrib-httpdomain',
            'sphinx_rtd_theme',
            'sphinx-autobuild',
        ],
    },
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
