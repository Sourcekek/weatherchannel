"""Simmer SDK API client for live Polymarket execution."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SIMMER_API_BASE = "https://api.simmer.markets"
TRADE_SOURCE = "sdk:weatherchannel"


class SimmerClientError(Exception):
    """Raised when Simmer API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SimmerClient:
    """Thin wrapper around the Simmer SDK REST API.

    Simmer proxies Polymarket CLOB orders. We use their /api/sdk/trade
    endpoint for buys/sells and /api/sdk/portfolio for position management.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = SIMMER_API_BASE,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("SIMMER_API_KEY", "")
        if not self.api_key:
            raise SimmerClientError("SIMMER_API_KEY not set")
        self.base_url = base_url
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make authenticated request to Simmer SDK."""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                resp = httpx.get(url, headers=self._headers(), timeout=self.timeout)
            else:
                resp = httpx.request(
                    method, url, headers=self._headers(),
                    json=data, timeout=self.timeout,
                )
            if resp.status_code >= 400:
                body = resp.text
                logger.error("Simmer API %d: %s %s -> %s", resp.status_code, method, endpoint, body)
                raise SimmerClientError(f"HTTP {resp.status_code}: {body}", resp.status_code)
            return resp.json()
        except httpx.RequestError as e:
            logger.error("Simmer API request failed: %s %s -> %s", method, endpoint, e)
            raise SimmerClientError(f"Request failed: {e}") from e

    # --- Trading ---

    def buy(
        self,
        market_id: str,
        amount_usd: float,
        side: str = "yes",
        venue: str = "simmer",
    ) -> dict:
        """Buy shares in a market.

        Args:
            market_id: Simmer market UUID.
            amount_usd: USD amount to spend.
            side: "yes" or "no".
            venue: "simmer" ($SIM virtual) or "polymarket" (real USDC).

        Returns:
            Trade result dict with success, trade_id, shares_bought, etc.
        """
        return self._request("POST", "/api/sdk/trade", {
            "market_id": market_id,
            "side": side,
            "amount": amount_usd,
            "venue": venue,
            "source": TRADE_SOURCE,
        })

    def sell(
        self,
        market_id: str,
        shares: float,
        side: str = "yes",
        venue: str = "simmer",
    ) -> dict:
        """Sell shares in a market.

        Args:
            market_id: Simmer market UUID.
            shares: Number of shares to sell.
            side: "yes" or "no".
            venue: "simmer" ($SIM virtual) or "polymarket" (real USDC).

        Returns:
            Trade result dict with success, trade_id, etc.
        """
        return self._request("POST", "/api/sdk/trade", {
            "market_id": market_id,
            "side": side,
            "action": "sell",
            "shares": shares,
            "venue": venue,
            "source": TRADE_SOURCE,
        })

    # --- Portfolio ---

    def get_portfolio(self) -> dict:
        """Get portfolio summary: balance, exposure, positions count."""
        return self._request("GET", "/api/sdk/portfolio")

    def get_positions(self) -> list[dict]:
        """Get all open positions."""
        result = self._request("GET", "/api/sdk/positions")
        return result.get("positions", []) if isinstance(result, dict) else []

    # --- Markets ---

    def get_weather_markets(self) -> list[dict]:
        """Get active weather-tagged markets from Simmer."""
        result = self._request("GET", "/api/sdk/markets?tags=weather&status=active&limit=200")
        return result.get("markets", []) if isinstance(result, dict) else []

    def get_market_context(self, market_id: str, my_probability: float | None = None) -> dict:
        """Get market context with safeguards and edge analysis."""
        endpoint = f"/api/sdk/context/{market_id}"
        if my_probability is not None:
            endpoint += f"?my_probability={my_probability}"
        return self._request("GET", endpoint)

    def build_token_to_simmer_map(self) -> dict[str, str]:
        """Build mapping from Polymarket CLOB token ID → Simmer market UUID.

        Each Simmer market has a `polymarket_token_id` field that corresponds
        to the CLOB YES token ID from Gamma API.
        """
        markets = self.get_weather_markets()
        mapping: dict[str, str] = {}
        for m in markets:
            poly_token = m.get("polymarket_token_id", "")
            simmer_id = m.get("id", "")
            if poly_token and simmer_id:
                mapping[poly_token] = simmer_id
        return mapping
