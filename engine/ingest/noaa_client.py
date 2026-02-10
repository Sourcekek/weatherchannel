"""NOAA/NWS forecast API client with retry and rate limit handling."""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

NOAA_BASE_URL = "https://api.weather.gov"
DEFAULT_USER_AGENT = "weatherchannel-engine/0.1.0"


class NoaaClient:
    def __init__(
        self,
        base_url: str = NOAA_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 5.0,
    ):
        self.base_url = base_url
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def get_forecast(self, grid_id: str, grid_x: int, grid_y: int) -> dict:
        """Fetch 7-day forecast from NOAA gridpoints endpoint.

        Retries on 503/429 with exponential backoff.
        """
        url = f"{self.base_url}/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast"
        headers = {"User-Agent": self.user_agent, "Accept": "application/geo+json"}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code in (503, 429) and attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)
                    logger.warning(
                        "NOAA %s returned %d, retrying in %.1fs (attempt %d/%d)",
                        url, resp.status_code, delay, attempt + 1, self.max_retries,
                    )
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)
                    logger.warning(
                        "NOAA request error, retrying in %.1fs: %s", delay, e
                    )
                    time.sleep(delay)
                    continue
                raise

        assert last_error is not None
        raise last_error
