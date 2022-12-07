echo "[*] Spinning up mysql through docker"
docker run -p 3306:3306 --name mysql \
    -e MYSQL_ALLOW_EMPTY_PASSWORD=1  \
    -e MYSQL_ROOT_HOST=% \
    -d mysql/mysql-server:8.0
