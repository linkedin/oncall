#!/usr/bin/env python
# -*- coding:utf-8 -*-

import setuptools
import re

with open('src/oncall/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

with open('README.md', 'r') as fd:
    long_description = fd.read()

setuptools.setup(
    name='oncall',
    version=version,
    description='Oncall is a calendar tool designed for scheduling and managing on-call shifts',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/linkedin/oncall',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3'
    ],
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    include_package_data=True,
    install_requires=[
        'falcon==3.1.1',
        'falcon-cors',
        'greenlet==2.0.1',
        'gevent==22.10.2',
        'asn1crypto==1.0.0',
        'ujson',
        'markupsafe==2.0.1',
        'sqlalchemy<2.0.0',
        'PyYAML',
        'PyMYSQL',
        'phonenumbers',
        'jinja2==3.0.3',
        'webassets',
        'beaker',
        'cryptography==3.1',
        'python-ldap',
        'pytz',
        'irisclient',
        'slackclient==1.3.1',
        'icalendar',
        'pymsteams',
        'idna==2.10'
    ],
    extras_require={
        'ldap': ['python-ldap'],
        'prometheus': ['prometheus_client'],
        'dev': [
            'pytest==7.1.2',
            'pytest-mock',
            'requests',
            'gunicorn==20.1.0',
            'flake8==6.0.0',
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
