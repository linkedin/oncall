```mkdir output```
```python gen_packer_cfg.py ./oncall.yaml | tail -n +2 > ./output/oncall.json```
```packer build -only=docker oncall.json```
```docker run --name oncall-mysql -e MYSQL_ROOT_PASSWORD='1234' -d mysql```
```docker run -d --link oncall-mysql:mysql -p 8080:8080 -e DOCKER_DB_BOOTSTRAP=1 quay.io/iris/oncall```

