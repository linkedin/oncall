#!/bin/bash

for i in `seq 1 5`; do
    mysql -h 127.0.0.1 -u root --password=1234 -e 'show databases;' && break
    echo "[*] Waiting for mysql to start..."
    sleep 5
done

echo "[*] Loading MySQL schema..."
mysql -h 127.0.0.1 -u root --password=1234 < ./db/schema.v0.sql
echo "[*] Loading MySQL dummy data..."
mysql -h 127.0.0.1 -u root --password=1234 -o oncall < ./db/dummy_data.sql

echo "[*] Tables created for database oncall:"
mysql -h 127.0.0.1 -u root --password=1234 -o oncall -e 'show tables;'
