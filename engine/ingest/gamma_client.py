"""Gamma API client for Polymarket event and market data."""

import logging

import httpx

logger = logging.getLogger(__name__)

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


class GammaClient:
    def __init__(self, base_url: str = GAMMA_BASE_URL, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    def get_event_by_slug(self, slug: str) -> dict | None:
        """Fetch a single event by slug. Returns None if not found."""
        url = f"{self.base_url}/events"
        params = {"slug": slug}
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            # Gamma returns a list; we want the first match
            if isinstance(data, list):
                return data[0] if data else None
            return data
        except httpx.HTTPStatusError as e:
            logger.error("Gamma API error for slug=%s: %s", slug, e)
            raise
        except httpx.RequestError as e:
            logger.error("Gamma API request failed for slug=%s: %s", slug, e)
            raise

    def get_active_weather_events(self, slugs: list[str]) -> list[dict]:
        """Fetch multiple events by slug list. Skips missing (404) events."""
        results = []
        for slug in slugs:
            try:
                event = self.get_event_by_slug(slug)
                if event is not None:
                    results.append(event)
            except (httpx.HTTPStatusError, httpx.RequestError):
                logger.warning("Skipping slug=%s due to API error", slug)
        return results
