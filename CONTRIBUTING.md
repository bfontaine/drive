# Contributing to Drive

## Run the tests

    poetry run pytest

On Linux, you may have to do this:

    LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu poetry run pytest

(FIXME: fix the underlying issue)

## Release a new version

1. Update the CHANGELOG
2. Update the version in `pyproject.toml` and in `drive/__init__.py`
3. Commit and tag with `v` followed by the version (e.g. `git tag v1.1.1`)
4. Push (without the tag) and wait for the [CI job][ci1] to succeed
5. Push the tag
6. Wait for the [CI job][ci2] to finish

[ci1]: https://github.com/bfontaine/drive/actions/workflows/build.yml
[ci2]: https://github.com/bfontaine/drive/actions/workflows/publish.yml
