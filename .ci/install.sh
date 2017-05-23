#!/bin/bash

bash .ci/run_mysql_docker.sh
sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev
python setup.py develop
pip install -r dev_requirements.txt

bash .ci/setup_mysql.sh
