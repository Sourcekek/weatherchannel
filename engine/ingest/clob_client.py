"""CLOB API client for price history data."""

import logging

import httpx

logger = logging.getLogger(__name__)

CLOB_BASE_URL = "https://clob.polymarket.com"


class ClobClient:
    def __init__(self, base_url: str = CLOB_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    def get_price_history(
        self, token_id: str, interval: str = "1d", fidelity: int = 60
    ) -> list[dict]:
        """Fetch price history for a CLOB token."""
        url = f"{self.base_url}/prices-history"
        params = {
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        }
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("history", []) if isinstance(data, dict) else []
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                "CLOB price history error for token=%s: %s", token_id, e
            )
            raise
