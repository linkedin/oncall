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
```

Setup app config by editing configs/config.yaml.


Run
---

One of the following commands:

* `goreman start`
* `procman start`
* `make serve`
* `oncall-dev ./configs/config.yaml`


Test
---

```bash
make test
```
