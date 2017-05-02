Oncall
======

Initial setup
-------------

Install dependencies:

```
pip install -r requirements.txt
python setup.py develop
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
