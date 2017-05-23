Admin guide
===========

Quickstart
----------

Test with Docker
````````````````

.. _Docker: https://www.docker.com/community-edition

A local test instance of Oncall can be setup with Docker_ in two commands:

.. code-block:: bash

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
