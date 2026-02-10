"""Market scanner: discovers active weather events across cities and dates."""

import json
import logging
import time
from datetime import date, timedelta

from engine.config.schema import EngineConfig
from engine.ingest.gamma_client import GammaClient
from engine.ingest.slug_parser import build_event_slug, parse_bucket_suffix
from engine.models.market import BucketMarket, MarketEvent

logger = logging.getLogger(__name__)


class MarketScanner:
    def __init__(self, config: EngineConfig, gamma_client: GammaClient):
        self.config = config
        self.gamma = gamma_client

    def scan(self, today: date | None = None) -> list[tuple[MarketEvent, str]]:
        """Scan for active weather events across all enabled cities and dates.

        Returns list of (MarketEvent, raw_json) tuples.
        """
        if today is None:
            today = date.today()

        results: list[tuple[MarketEvent, str]] = []
        enabled_cities = [c for c in self.config.cities if c.enabled]

        for city in enabled_cities:
            for day_offset in range(self.config.ops.lookahead_days):
                target = today + timedelta(days=day_offset)
                slug = build_event_slug(
                    city.slug, target.year, target.month, target.day
                )
                try:
                    raw_event = self.gamma.get_event_by_slug(slug)
                    if raw_event is None:
                        logger.debug("No event for slug=%s", slug)
                        continue

                    event = _parse_gamma_event(raw_event, city.slug, str(target))
                    if event is not None:
                        results.append((event, json.dumps(raw_event)))
                        logger.info(
                            "Found event: %s with %d buckets",
                            slug, len(event.buckets),
                        )

                except Exception:
                    logger.exception("Error scanning slug=%s", slug)

                # Rate limiting
                delay_s = self.config.ops.request_delay_ms / 1000.0
                if delay_s > 0:
                    time.sleep(delay_s)

        return results


def _parse_gamma_event(
    raw: dict, city_slug: str, target_date: str
) -> MarketEvent | None:
    """Parse a Gamma API event response into a MarketEvent."""
    event_id = str(raw.get("id", ""))
    slug = raw.get("slug", "")
    title = raw.get("title", "")
    markets = raw.get("markets", [])

    if not event_id or not markets:
        return None

    buckets: list[BucketMarket] = []
    for m in markets:
        bm = _parse_bucket_market(m, event_slug=slug)
        if bm is not None:
            buckets.append(bm)

    if not buckets:
        logger.warning("No parseable buckets for event %s", slug)
        return None

    return MarketEvent(
        event_id=event_id,
        slug=slug,
        city_slug=city_slug,
        target_date=target_date,
        title=title,
        buckets=buckets,
    )


def _parse_bucket_market(m: dict, event_slug: str = "") -> BucketMarket | None:
    """Parse a single market from Gamma API into a BucketMarket."""
    try:
        # Parse CLOB token IDs from JSON string
        clob_ids_raw = m.get("clobTokenIds", "[]")
        clob_ids = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        if len(clob_ids) < 2:
            return None

        # Parse outcome prices
        prices_raw = m.get("outcomePrices", "[]")
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw

        price_yes = float(prices[0]) if prices else 0.0

        # Parse bucket from group item title or slug
        group_title = m.get("groupItemTitle", "")
        slug = m.get("slug", "")

        # Extract bucket suffix from market slug.
        # Market slug = event_slug + "-" + bucket_suffix
        # e.g. "highest-temperature-in-nyc-on-february-11-2026-34-35f"
        # event_slug = "highest-temperature-in-nyc-on-february-11-2026"
        # bucket_suffix = "34-35f"
        bucket = None
        if slug and event_slug and slug.startswith(event_slug + "-"):
            suffix = slug[len(event_slug) + 1:]
            parsed = parse_bucket_suffix(suffix)
            if parsed is not None:
                bucket = parsed.bucket

        # Fallback: try legacy "-be-" separator
        if bucket is None and slug:
            parts = slug.rsplit("-be-", 1)
            if len(parts) == 2:
                parsed = parse_bucket_suffix(parts[1])
                if parsed is not None:
                    bucket = parsed.bucket

        if bucket is None:
            logger.debug("Could not parse bucket from slug=%s", slug)
            return None

        return BucketMarket(
            market_id=str(m.get("id", "")),
            condition_id=str(m.get("conditionId", "")),
            clob_token_id_yes=str(clob_ids[0]),
            clob_token_id_no=str(clob_ids[1]),
            outcome_price_yes=price_yes,
            best_bid=float(m.get("bestBid", 0)),
            best_ask=float(m.get("bestAsk", 0)),
            last_trade_price=float(m.get("lastTradePrice", 0)),
            liquidity=float(m.get("liquidity", 0)),
            volume_24hr=float(m.get("volume24hr", 0)),
            maker_base_fee=float(m.get("makerBaseFee", 0)),
            taker_base_fee=float(m.get("takerBaseFee", 0)),
            order_min_size=float(m.get("orderMinSize", 0)),
            accepting_orders=bool(m.get("acceptingOrders", False)),
            end_date=str(m.get("endDate", "")),
            group_item_title=group_title,
            group_item_threshold=str(m.get("groupItemThreshold", "")),
            bucket=bucket,
        )
    except (KeyError, ValueError, IndexError) as e:
        logger.debug("Failed to parse bucket market: %s", e)
        return None
