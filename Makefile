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

check:
	make static-analysis
	make test

.PHONY: test e2e
