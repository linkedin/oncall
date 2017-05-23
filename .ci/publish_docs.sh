#!/bin/bash

echo "Building documentation..."
pushd docs && {
    rm -rf build
    make html
} || exit 1; popd

mv docs/build/html ./

echo "Switching to gh-pages branch..."
git checkout gh-pages || {
    echo "Failed to check out gh-pages branch"
    exit 1
}
rm -rf docs
mv html docs
git add docs
git commit -m "Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`"

echo "Pushing gh-pages branch..."
git remote add tmp_upstream_docs git@github.com:linkedin/oncall.git
git push tmp_upstream_docs gh-pages:gh-pages
git remote rm tmp_upstream_docs

echo "Switching back to master branch..."
git checkout master
