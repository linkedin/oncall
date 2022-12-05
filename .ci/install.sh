#!/bin/bash

bash .ci/run_mysql_docker.sh
sudo apt-get update
sudo apt-get install libsasl2-dev python3-dev libldap2-dev libssl-dev
python setup.py develop
pip install -e .[dev]

bash .ci/setup_mysql.sh
