Admin guide
===========

Quickstart
----------

Test with Docker
````````````````

.. _Docker: https://www.docker.com/community-edition
.. _DockerCompose: https://docs.docker.com/compose/

A local test instance of Oncall can be setup with Docker_ and
DockerCompose_ in a single command:

.. code-block:: bash

    docker-compose up

The above command sets up an Oncall service and MySQL database. Note that we
set the MySQL root password to '1234'; you may wish to change this to something
more secure.

Details about the container configuration are in ``docker-compose.yml`` and
``Dockerfile``.  During the first run the database schema will be created and
populated with some dummy data.  You can edit the dummy data in
``./db/dummy_data.sql``, but you will need to stop and recreate your containers
to load your new data.

.. code-block:: bash

    docker-compose stop
    docker-compose rm -f
    docker-compose build
    docker-compose up

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


Ldap Authentication
```````````````````

Alternatively, you can configure oncall ldap authentication to use the `oncall.auth.modules.ldap_import` module.
When a user try to connect to oncall, the module will check if the user is already present or not.
If not, the user will be automatically added to the oncall user database, and conacts information will be synced.
If the user already exists, his contacts informations will be updated according to ldap informations.
You can deactivate this feature by setting the `import_user` option to `False`.

Here is an example of ldap auth configuration :

.. code-block:: yaml

    auth:
      debug: False
      module: 'oncall.auth.modules.ldap_import'
      ldap_url: 'ldaps://ldapserver.org'
      ldap_user_suffix: ''
      ldap_cert_path: '/etc/ldap_cert.pem'
      ldap_bind_user: 'cn=oncall,ou=serviceaccount,dc=company,dc=org'
      ldap_bind_password: 'xxxx'
      ldap_base_dn: 'ou=accounts,dc=company,dc=org'
      ldap_search_filter: '(uid=%s)'
      import_user: True
      attrs:
        username: 'uid'
        full_name: 'cn'
        email: 'mail'
        call: '0123456789'
        sms: '0123456789'
        slack: 'uid'

Note if one of the attrs for ldap mapping to oncall contacts information is missing in ldap, the configured attr value will be used as the default value. 
For example if the ldap does not have a phone attribute for a user, the default valut will be the 0123456789 call number.


Iris Integration
````````````````
To allow Oncall users to escalate issues via Iris, you will need to configure
the ``iris_plan_integration`` section of the Oncall config. This lets you define
a dynamic Iris plan for urgent and non-urgent escalations from the Oncall
frontend, and also allows teams to define a custom escalation plan that may
be triggered. The example Iris/Oncall installations should be configured with a
working Oncall escalation plan called "Oncall test". To configure this setting,
do the following:

1. In the Iris frontend logged in as an admin user (demo by default), create an application corresponding to Oncall ("oncall" in the example data). This application must define the "requester" and "description" variables.
#. Update the Oncall config file with this name, along with the Iris API key and host
#. Create a template in Iris that has an application template for Oncall.
#. Create a dynamic plan in Iris ("Oncall test" in the example).
#. Ensure CORS is allowed from Oncall to Iris in the Iris configuration file.
#. Update the Oncall config file with this dynamic plan name, and map roles/targets to that plan's dynamic targets. In the example, target 0 in "Oncall test" maps to a team's primary oncall, target 1 maps to all members of the team, and target 2 maps to the manager of the team.
#. Test the integration via the Oncall frontend. Oncall should create an Iris incident and trigger the configured Iris plan's escalation steps.
