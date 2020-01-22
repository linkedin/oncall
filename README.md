Oncall [![Gitter chat](https://badges.gitter.im/irisoncall/Lobby.png)](https://gitter.im/irisoncall/Lobby) [![Build Status](https://circleci.com/gh/linkedin/oncall.svg?style=shield)](https://circleci.com/gh/linkedin/oncall)
======

<p align="center"><img src="https://github.com/linkedin/oncall/raw/master/docs/source/_static/demo.png" width="600"></p>

See [admin docs](http://oncall.tools/docs/admin_guide.html) for information on
how to run and manage Oncall.

Development setup
-----------------
### Prerequisites

  * Debian/Ubuntu - `sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev python-pip python-setuptools mysql-server mysql-client libffi-dev libyaml-cpp-dev python-dateutil`

### Install

```bash
python setup.py develop
pip install -e '.[dev]'
```

Setup mysql schema:

```bash
mysql -u root -p < ./db/schema.v0.sql
```

Setup app config by editing configs/config.yaml.

Optionally, you can import dummy data for testing:

```bash
mysql -u root -p -o oncall < ./db/dummy_data.sql
```

### Run

One of the following commands:

* `goreman start`
* `procman start`
* `make serve`
* `oncall-dev ./configs/config.yaml`


### Test

```bash
make test
```

Check out https://github.com/linkedin/oncall/issues for a list of outstanding
issues, and tackle any one that catches your interest. Contributions are
expected to be tested thoroughly and submitted with unit/end-to-end tests; look
in the e2e directory for our suite of end-to-end tests.
