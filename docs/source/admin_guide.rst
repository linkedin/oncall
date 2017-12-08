Admin guide
===========

Quickstart
----------

Test with Docker
````````````````

.. _Docker: https://www.docker.com/community-edition

A local test instance of Oncall can be setup with Docker_ in a few commands:

.. code-block:: bash

    cd ./ops/packer
    mkdir output
    python gen_packer_cfg.py ./oncall.yaml | tail -n +2 > ./output/oncall.json
    packer build -only=docker oncall.json
    docker run -d --name oncall-mysql -e MYSQL_ROOT_PASSWORD='1234' mysql
    docker run -d --link oncall-mysql:mysql -p 8080:8080 -e DOCKER_DB_BOOTSTRAP=1 quay.io/iris/oncall

.. NOTE::
    We pass a **DOCKER_DB_BOOTSTRAP** environment variable to the Oncall container
    indicating to our setup script that the database needs to be initialized. This
    will populate the database with a small amount of dummy data and set up the
    proper schema so we can get up and running.

The above commands set up an Oncall service and MySQL database. Note that we
set the MySQL root password to '1234'; you may wish to change this to something
more secure.

The test instance of Oncall can be accessed at http://localhost:8080.  Try
logging in as the user "jdoe", with any password (the Docker image defaults to
disable authentication, which authenticates all credentials so long as the user
exists in the DB). You can navigate to the "Browse Teams" page and check out
"Test Team", which shows a calendar page where you can create and modify
events. See :ref:`user-guide` for more information on how to interact with the
UI.

Adding Users
````````````

Users may be imported from other systems such as LDAP and Slack. This process is
extensible by developing your own plugins.

Let's use LDAP as an example. First we configure the user_sync process to use the
ldap_sync module, then we provide specific configuration for this module to
connect to LDAP.

.. code-block:: yaml

    user_sync:
      module: 'oncall.user_sync.ldap_sync'

    ldap_sync:
      url: 'ldaps://ldapserver.org'
      base: 'ou=accounts,dc=company,dc=org'
      user: 'cn=oncall,ou=serviceaccount,dc=company,dc=org'
      password: 'xxxx'
      cert_path: '/etc/ldap_cert.pem'
      query: '(uid=*)'
      attrs:
        username: 'uid'
        full_name: 'cn'
        mail: 'mail'
        mobile: 'mobile'
      image_url: 'https://image.example.com/api/%s/picture'

User synchronization is a seperate process which needs to be started manually,
but will continue to run in a loop, updating users as necessary.

To run this process, you simply point to the configuration file:

.. code-block:: bash

    ./oncall-user-sync /home/oncall/config/config.yaml

Now that your users are in Oncall, they can be accessed by Iris. Note that
this too is a manually triggered synchronization process, rather than just
a call to Oncall. But while Iris will import these as Targets, it will still
call Oncall to determine who is the current Oncall-primary and secondary, when
creating a new message to be sent.

.. _Oncall-admin: https://github.com/dwang159/oncall-admin

.. NOTE::
    It is also possible to use Oncall-admin_ to do manual user administration
