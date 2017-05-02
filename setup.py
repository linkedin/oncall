#!/usr/bin/env python
# -*- coding:utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import re
o
with open('src/oncall/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

setup(
    name='oncall',
    version=version,
    packages=['oncall'],
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'build_assets = oncall.bin.build_assets:main',
            'oncall-scheduler = oncall.bin.scheduler:main',
            'oncall-notifier = oncall.bin.notifier:main'
        ]
    }
)
