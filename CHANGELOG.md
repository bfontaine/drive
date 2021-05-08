# Drive Changelog

## 0.3.0 (2021/05/08)

* Downloaded workbooks are no longer read-only by default. If you want to get that behavior back, pass `read_only=True`
  to `File.download_workbook` and `Client.download_excel_workbook`.
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
