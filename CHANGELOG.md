# Drive Changelog

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
