all: serve

serve:
	oncall-dev ./configs/config.yaml

unit:
	py.test -v ./test

e2e:
	py.test -v ./e2e

test:
	make unit
	make e2e

static-analysis:
	pyflakes test src

flake8:
	flake8 src test setup.py

check:
	make static-analysis
	make flake8
	make test

.PHONY: test e2e

APP_NAME=oncall

build:
	docker build --ulimit nofile=1024 -t $(APP_NAME) .

run: build
	docker run -p 8080:8080 $(APP_NAME)