echo "[*] Spinning up mysql through docker"
docker run -p 3306:3306 --name mysql \
    -e MYSQL_ALLOW_EMPTY_PASSWORD=1  \
    -e MYSQL_ROOT_HOST=172.17.0.1 \
    -d mysql/mysql-server:5.7
