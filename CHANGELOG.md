# Drive Changelog

## 0.4.4 (2023/06/30)

* Rename parameter `sleep` of `SheetClient.iter_sheet_lines` as `sleep_for` (keep `sleep` as an alias)
* Add auto-retry on 500/503 errors when querying a spreadsheet.
* Add `SheetClient.iter_sheet_lines_as_dicts`
* Add missing docstrings to `SheetClient`

## 0.4.3 (2023/06/27)

* Add an optional offset in `SheetClient.iter_sheet_lines`

## 0.4.2 (2023/06/26)

* Fix `get_credentials` to respect `ENV_CLIENT_SECRET_PATH`
* Raise a `MissingCredentialsException` instead of `KeyError` if no credentials are given
  and `GOOGLE_APPLICATION_CREDENTIALS` is not set
* Add `auth.authorize_credentials` as a shortcut for `authorize(get_credentials(…))`
* Add a basic, experimental Google Sheets client in `drive.sheets`. The code is production-ready but the API may change
  in the future.

## 0.4.1 (2023/05/15)

* Raise a more explicit exception when `upload()` or `upload_file()` is used without an explicit `original_mime_type`
  and libmagic is not installed (#11).
* Fix the type hint of `parent_id`, which can be a `File` or a `str`
* Add official support for Python 3.11

## 0.4.0 (2022/10/12)

* Use `google-api-python-client` 2.64.0+
* Use minimum versions for dependencies instead of strict versions
* Add `download_retries_count` optional keyword argument to `Client`
* `get_or_create_folder` now raises `RuntimeError` instead of `NameError` if there is an issue finding the folder
* Fix type hints of `create_folder`
* Add `py.typed` to indicate that this module is typed
* Use Poetry to manage the project

## 0.3.2 (2021/06/02)

* Use `google-api-python-client` 2.7.0
* Add `File#grant_permissions` and `File#get_web_view_link` ([code][perms-code] by @pavel-hamernik)
* `File#download_file`, `File#download_workbook` and `File#get_child` now return `None` instead of `False`
  if `._client` isn’t set
* `File#exists` now returns `None` instead of `False` if `._client` isn’t set
* `File#download_workbook` now has a correct return type hint: `Optional[Workbook]` instead of `bool`
* Remove three `client.Client` private methods (`_serialize_query_value`, `_make_query_clause`, `_make_querystring`)

[perms-code]: https://github.com/NoName115/drive/commit/eec799000d1367bf17b5c6f80b655db0ca95b3de

## 0.3.1 (2021/05/20)

* Use `google-api-python-client` 1.12.8

## 0.3.0 (2021/05/08)

* Downloaded workbooks are no longer read-only by default. If you want to get that behavior back, pass `read_only=True`
  to `File.download_workbook` and `Client.download_excel_workbook`. This fixes #6.
* Use `openpyxl` 3.0.7

## 0.2.4 (2021/02/04)

* Fix `download_file` (#4; reported and fixed by @thapr0digy)

Note: 0.2.3 is exactly like 0.2.2.

## 0.2.2 (2020/06/16)

* Add more documentation
* Add type hints

## 0.2.1 (2020/06/15)

* Remove a dependency on an internal package
* Add `drive.mimetypes`

## 0.2.0 (2019/08/08)

Initial public release.
