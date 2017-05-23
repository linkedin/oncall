Oncall [![Gitter chat](https://badges.gitter.im/irisoncall/Lobby.png)](https://gitter.im/irisoncall/Lobby)
======

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
