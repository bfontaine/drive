import time
from typing import Iterable, Optional

from googleapiclient import discovery  # type: ignore

from .auth import authorize_credentials

__all__ = ['SheetClient']


class SheetClient:
    """Experimental Google Sheets client."""

    def __init__(self, credentials_path: Optional[str] = None):
        http = authorize_credentials(credentials_path)
        service = discovery.build('sheets', 'v4', http=http)
        self.service = service.spreadsheets()

    def get_sheet_range(self, sheet_id: str, sheet_tab: str, cell_range: str):
        req = self.service.values().get(spreadsheetId=sheet_id, range=f"{sheet_tab}!{cell_range}")
        # Note this often raises errors 500 or 503
        resp = req.execute()
        return resp["values"]

    def iter_sheet_lines(self, sheet_id: str, sheet_tab: str, column_start: str, column_end: str,
                         *, batch_size=400, sleep=0.5) \
            -> Iterable[list]:
        offset = 1  # lines start at 1
        while True:
            cell_range = f"{column_start}{offset}:{column_end}{offset + batch_size}"
            lines = self.get_sheet_range(sheet_id, sheet_tab, cell_range)
            yield from lines
            if len(lines) < batch_size:
                break
            offset += batch_size
            if sleep > 0:
                # Don't hammer the API
                # https://developers.google.com/sheets/api/reference/limits
                time.sleep(sleep)
