#! /bin/bash -ex
[ ! -f pyproject.toml ] && exit 0

COV_ARGS=""

if [ -n "$HTMLCOV" ]; then
  COV_ARGS="$COV_ARGS --cov-report=html"
fi
if [ -n "$BRANCHCOV" ]; then
  COV_ARGS="$COV_ARGS --cov-branch"
fi

poetry run ruff check drive
poetry run mypy --check-untyped-defs --explicit-package-bases drive
poetry run pytest --cov=drive $COV_ARGS tests/
