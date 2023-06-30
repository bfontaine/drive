import time
from typing import Iterable, Optional, Callable, TypeVar, Dict, List, Any

from googleapiclient import discovery  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from .auth import authorize_credentials

__all__ = ['SheetClient', 'sheet_lines_as_dicts']

T = TypeVar('T')


def _auto_retry(fn: Callable[[], T], *,
                max_retries=2,
                sleep_for=4) -> T:
    while True:
        try:
            return fn()
        except HttpError as e:
            if e.status_code in {500, 503} and max_retries > 0:
                max_retries -= 1
                time.sleep(sleep_for)
                continue

            raise


class SheetClient:
    """Google Sheets client."""

    def __init__(self, credentials_path: Optional[str] = None):
        http = authorize_credentials(credentials_path)
        service = discovery.build('sheets', 'v4', http=http)
        self.service = service.spreadsheets()

    def get_sheet_range(self, sheet_id: str, sheet_tab: str, cell_range: str,
                        *, max_retries=2):
        """
        Get a range of cells from a spreadsheet.

        :param sheet_id:
        :param sheet_tab:
        :param cell_range: Range, like A1:B3 to get columns A-B of lines 1-3.
        :param max_retries: Max retries on 5XX errors
        :return:
        """
        req = self.service.values().get(spreadsheetId=sheet_id, range=f"{sheet_tab}!{cell_range}")
        # Note this often raises errors 500 or 503
        resp = _auto_retry(req.execute, max_retries=max_retries)
        return resp["values"]

    def iter_sheet_lines(self, sheet_id: str, sheet_tab: str, column_start: str, column_end: str,
                         *,
                         offset=0,
                         batch_size=400,
                         sleep_for=0.5,
                         sleep: Optional[float] = None) \
            -> Iterable[list]:
        """
        Iterate over lines of a spreadsheet: fetch them in batches and yield one at a time.

        :param sheet_id: spreadsheet ID
        :param sheet_tab: tab name
        :param column_start: first column (example: "A")
        :param column_end: last column (example: "Z")
        :param offset: start reading at this offset
        :param batch_size: how many lines to fetch at a time.
        :param sleep_for: sleep this amount of time between batch calls.
        :param sleep: deprecated alias for sleep_for.
        :return:
        """

        if sleep is not None:
            sleep_for = sleep

        offset += 1  # lines start at 1
        while True:
            cell_range = f"{column_start}{offset}:{column_end}{offset + batch_size}"
            lines = self.get_sheet_range(sheet_id, sheet_tab, cell_range)
            yield from lines
            if len(lines) < batch_size:
                break
            offset += batch_size
            if sleep_for > 0:
                # Don't hammer the API
                # https://developers.google.com/sheets/api/reference/limits
                time.sleep(sleep_for)

    def iter_sheet_lines_as_dicts(self, sheet_id: str, sheet_tab: str,
                                  column_start: str, column_end: str,
                                  *,
                                  fieldnames: Optional[Iterable[Any]] = None,
                                  restkey=None,
                                  restval=None,
                                  **kwargs) -> Iterable[dict]:
        """
        Equivalent of `sheet_lines_as_dicts(client.iter_sheet_lines(...))`.
        All trailing keyword arguments are passed to `iter_sheet_lines`.
        """
        return sheet_lines_as_dicts(
            self.iter_sheet_lines(
                sheet_id=sheet_id,
                sheet_tab=sheet_tab,
                column_start=column_start,
                column_end=column_end,
                **kwargs,
            ),
            fieldnames=fieldnames,
            restkey=restkey,
            restval=restval,
        )


def sheet_lines_as_dicts(lines: Iterable[List[Any]],
                         fieldnames: Optional[Iterable[Any]] = None,
                         *,
                         restkey=None,
                         restval=None) -> Iterable[dict]:
    """
    Transform spreadsheet lines into dictionaries like `csv.DictReader`. Aside from the first one, all the arguments
    match `csv.DictReader`’s API.

    See https://docs.python.org/3/library/csv.html#csv.DictReader.

    :param lines: spreadsheet lines.
    :param fieldnames: field names to use. If omitted, the first line is used as a header.
    :param restkey:
    :param restval:
    :return:
    """
    # cell index -> header key
    cell_index_mapping: Dict[int, Any] = {}
    empty_line = {}

    first = True
    if fieldnames is not None:
        first = False
        for i, field_name in enumerate(fieldnames):
            cell_index_mapping[i] = field_name
        empty_line = {field: restval for field in cell_index_mapping.values()}

    for line in lines:
        if first:
            for i, value in enumerate(line):
                cell_index_mapping[i] = value
            empty_line = {field: restval for field in cell_index_mapping.values()}
            first = False
            continue

        m = dict(empty_line)

        for i, value in enumerate(line):
            if i in cell_index_mapping:
                m[cell_index_mapping[i]] = value
            else:
                m.setdefault(restkey, [])
                m[restkey].append(value)

        yield m
