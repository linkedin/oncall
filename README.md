Oncall [![Gitter chat](https://badges.gitter.im/irisoncall/Lobby.png)](https://gitter.im/irisoncall/Lobby)
======
---


Quickstart
-------------
### For users
To set up a local instance of Oncall, we recommend using Docker. Docker is available for download at https://www.docker.com/community-edition. We have a publicly available Docker image that can be set up using just two commands. After downloading docker, use 
```docker run --name oncall-mysql -e MYSQL_ROOT_PASSWORD='1234' -d mysql```
to set up a MySQL database for Oncall to run with. Note that we set the MySQL root password to '1234'; you may wish to change this to something more secure.

After setting up the mysql container, we can set up an instance of Oncall running on http://localhost:8080 with the following:
```docker run -d --link oncall-mysql:mysql -p 8080:8080 -e DOCKER_DB_BOOTSTRAP=1 quay.io/iris/oncall```
Here, we link the mysql container created in the previous step with our Oncall container, allowing for easy MySQL access between the two containers. We also pass a DOCKER_DB_BOOTSTRAP environment variable indicating to our setup script that the database needs to be initialized. This will populate the database with a small amount of dummy data and set up the proper schema so we can get up and running.

Once these two steps are complete, you can visit localhost:8080 in your browser to check out Oncall. Try logging in as the user "jdoe", with any password (the Docker image defaults to debug authentication, which authenticates all credentials so long as the user exists in the DB). You can navigate to the "Browse Teams" page and check out "Test Team", which shows a calendar page where you can create and modify events.


### For developers


<img src="https://github.com/linkedin/oncall/raw/master/src/oncall/ui/static/images/oncall_logo_blue.png" width="100">


Initial setup
-------------
### Prerequisites

  * Debian/Ubuntu - `sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev`

### Install

```
python setup.py develop
pip install -r dev_requirements.txt
```

Setup mysql schema:

```
mysql -u root -p < ./db/schema.v0.sql
mysql -u root -p < ./db/dummy_data.sql
```

Setup app config by editing configs/config.yaml.


Run
---

One of the following commands:

* `goreman start`
* `procman start`
* `make serve`
* `oncall-dev ./configs/config.yaml`

This sets up a local instance of Oncall on localhost:8080 with gunicorn. Try logging in as the user "jdoe", with any password (the Docker image defaults to debug authentication, which authenticates all credentials so long as the user exists in the DB). You can navigate to the "Browse Teams" page and check out "Test Team", which     shows a calendar page where you can create and modify events.

Any changes made should be automatically picked up and displayed on refresh. Check out https://github.com/linkedin/oncall/issues for a list of outstanding issues, and tackle any one that catches your interest. Contributions are expected to be tested thoroughly and submitted with unit/end-to-end tests; look in the e2e directory for our suite of end-to-end tests.


Test
---

```bash
make test
```
