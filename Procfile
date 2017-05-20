web: oncall-dev ./configs/config.yaml --skip-build-assets
assets: build_assets watch
doc: bash -c 'cd docs && sphinx-autobuild -H 0.0.0.0 -p ${PORT} --ignore '*~' source build/html/'
