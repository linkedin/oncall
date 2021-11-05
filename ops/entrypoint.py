# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import subprocess
import os
import socket
import time
import sys
from glob import glob
from oncall.utils import read_config

dbpath = '/home/oncall/db'
initializedfile = '/home/oncall/db_initialized'


def load_sqldump(config, sqlfile, one_db=True):
    print('Importing %s...' % sqlfile)
    with open(sqlfile) as h:
        cmd = ['/usr/bin/mysql', '-h', config['host'], '-u',
               config['user'], '-p' + config['password'],'-P' + str(config['port'])]
        if one_db:
            cmd += ['-o', config['database']]
        proc = subprocess.Popen(cmd, stdin=h)
        proc.communicate()

        if proc.returncode == 0:
            print('DB successfully loaded ' + sqlfile)
            return True
        else:
            print(('Ran into problems during DB bootstrap. '
                   'oncall will likely not function correctly. '
                   'mysql exit code: %s for %s') % (proc.returncode, sqlfile))
            return False


def wait_for_mysql(config):
    print('Checking MySQL liveness on %s...' % config['host'])
    db_address = (config['host'], config['port'])
    tries = 0
    while True:
        try:
            sock = socket.socket()
            sock.connect(db_address)
            sock.close()
            break
        except socket.error:
            if tries > 20:
                print('Waited too long for DB to come up. Bailing.')
                sys.exit(1)

            print('DB not up yet. Waiting a few seconds..')
            time.sleep(2)
            tries += 1
            continue


def initialize_mysql_schema(config):
    print('Initializing oncall database')
    # disable one_db to let schema.v0.sql create the database
    re = load_sqldump(config, os.path.join(dbpath, 'schema.v0.sql'), one_db=False)
    if not re:
        sys.exit('Failed to load schema into DB.')

    for f in glob(os.path.join(dbpath, 'patches', '*.sql')):
        re = load_sqldump(config, f)
        if not re:
            sys.exit('Failed to load DB patche: %s.' % f)

    re = load_sqldump(config, os.path.join(dbpath, 'dummy_data.sql'))
    if not re:
        sys.stderr.write('Failed to load dummy data.')

    with open(initializedfile, 'w'):
        print('Wrote %s so we don\'t bootstrap db again' % initializedfile)


def main():
    oncall_config = read_config(
        os.environ.get('ONCALL_CFG_PATH', '/home/oncall/config/config.yaml'))
    mysql_config = oncall_config['db']['conn']['kwargs']

    # It often takes several seconds for MySQL to start up. oncall dies upon start
    # if it can't immediately connect to MySQL, so we have to wait for it.
    wait_for_mysql(mysql_config)

    if 'DOCKER_DB_BOOTSTRAP' in os.environ:
        if not os.path.exists(initializedfile):
            initialize_mysql_schema(mysql_config)

    os.execv('/usr/bin/uwsgi',
             ['/usr/bin/uwsgi', '--yaml', '/home/oncall/daemons/uwsgi.yaml:prod'])


if __name__ == '__main__':
    main()
