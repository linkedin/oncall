all: serve

serve:
	@# python . ./configs/config.yaml
	gunicorn --reload --access-logfile=- -b '0.0.0.0:8080' --worker-class gevent \
		-w 4 -e CONFIG=./configs/config.yaml -t 500 \
		oncall.wrappers.gunicorn:application

test:
	py.test -v ./e2e
	py.test -v ./test

check:
	pyflakes test src

.PHONY: test
