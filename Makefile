all: serve

serve:
	oncall-dev ./configs/config.yaml

test:
	py.test -v ./e2e
	py.test -v ./test

check:
	pyflakes test src

.PHONY: test
