FROM ubuntu:16.04 as base

RUN apt-get update
RUN apt-get -y install libffi-dev libsasl2-dev python-dev libldap2-dev libssl-dev python-pip python-setuptools mysql-client

FROM base as envbase   

COPY setup.py /oncall/setup.py
COPY src/oncall/__init__.py /oncall/src/oncall/__init__.py

WORKDIR /oncall

RUN python setup.py develop
RUN pip install -e '.[dev]'

FROM envbase

COPY . /oncall
WORKDIR /oncall

EXPOSE 8080

ENTRYPOINT [ "oncall-dev", "./configs/config.yaml" ]
