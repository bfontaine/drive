import time
from typing import Iterable, Optional, Callable, TypeVar

from googleapiclient import discovery  # type: ignore
from googleapiclient.errors import HttpError

from .auth import authorize_credentials

__all__ = ['SheetClient']

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
