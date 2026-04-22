from __future__ import annotations
import requests

CSP_BASE = "https://commonstandardsproject.com/api/v1"
COMMON_CORE_JURISDICTION_ID = "67810E9EF6944F9383DCC602A3484C23"

ELA_SET_IDS = [
    f"{COMMON_CORE_JURISDICTION_ID}_D10003FC_grade-02",
    f"{COMMON_CORE_JURISDICTION_ID}_D10003FC_grade-03",
    f"{COMMON_CORE_JURISDICTION_ID}_D10003FC_grade-04",
]

class CSPClient:
    """Thin wrapper around the Common Standards Project API."""

    def __init__(self, api_key: str, base_url: str = CSP_BASE, timeout: int = 30):
        self._base = base_url
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Api-Key": api_key})

    def _get(self, path: str) -> dict:
        """Internal: do a GET, raise an error, return parsed JSON."""
        request = self._session.get(f"{self._base}{path}", timeout=self._timeout)
        request.raise_for_status()
        return request.json()
    
    def fetch_standard_set(self, set_id: str) -> dict:
        """GET /standard_sets/:id → returns the 'data' block."""
        return self._get(f"/standard_sets/{set_id}")["data"]

