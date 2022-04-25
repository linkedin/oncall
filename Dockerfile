FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::=--force-confold dist-upgrade \
    && DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::=--force-confold install libffi-dev libsasl2-dev python3-dev \
        sudo libldap2-dev libssl-dev python3-pip python3-setuptools python3-venv \
        mysql-client uwsgi uwsgi-plugin-python3 nginx \
    && rm -rf /var/cache/apt/archives/*

RUN useradd -m -s /bin/bash oncall

COPY src /home/oncall/source/src
COPY setup.py /home/oncall/source/setup.py
COPY MANIFEST.in /home/oncall/source/MANIFEST.in
COPY README.md /home/oncall/source/README.md
COPY LICENSE /home/oncall/source/LICENSE

WORKDIR /home/oncall

RUN chown -R oncall:oncall /home/oncall/source /var/log/nginx /var/lib/nginx \
    && sudo -Hu oncall mkdir -p /home/oncall/var/log/uwsgi /home/oncall/var/log/nginx /home/oncall/var/run /home/oncall/var/relay \
    && sudo -Hu oncall python3 -m venv /home/oncall/env \
    && sudo -Hu oncall /bin/bash -c 'source /home/oncall/env/bin/activate && cd /home/oncall/source && pip install wheel && pip install .'

COPY ops/config/systemd /etc/systemd/system
COPY ops/daemons /home/oncall/daemons
COPY ops/daemons/uwsgi-docker.yaml /home/oncall/daemons/uwsgi.yaml
COPY db /home/oncall/db
COPY configs /home/oncall/config
COPY ops/entrypoint.py /home/oncall/entrypoint.py

EXPOSE 8080

CMD ["sudo", "-EHu", "oncall", "bash", "-c", "source /home/oncall/env/bin/activate && python -u /home/oncall/entrypoint.py"]
