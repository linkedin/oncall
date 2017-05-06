Oncall
======

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

```
make serve
```


Test
---

```
make test
```
