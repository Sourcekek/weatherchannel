"""Parse Polymarket weather event and bucket market slugs."""

import re
from dataclasses import dataclass

from engine.models.market import BucketType, TemperatureBucket, TemperatureUnit

# City slug mapping for event slug construction
CITY_SLUG_MAP = {
    "nyc": "nyc",
    "chicago": "chicago",
    "seattle": "seattle",
    "atlanta": "atlanta",
    "dallas": "dallas",
}

MONTH_NAMES = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december",
}

# Bucket suffix patterns (order matters: more specific first)
# Handles negative temps via "neg" prefix and optional negative sign
_TEMP_PAT = r"(?:neg)?-?\d+"

BUCKET_PATTERNS = [
    # OR_HIGHER: "44forhigher" or "44corhigher"
    (
        re.compile(rf"^({_TEMP_PAT})(f|c)orhigher$"),
        BucketType.OR_HIGHER,
    ),
    # OR_BELOW: "33forbelow" or "33corbelow"
    (
        re.compile(rf"^({_TEMP_PAT})(f|c)orbelow$"),
        BucketType.OR_BELOW,
    ),
    # RANGE: "42-43f" or "42-43c" (handles negative: "neg1-2f")
    (
        re.compile(rf"^({_TEMP_PAT})-({_TEMP_PAT})(f|c)$"),
        BucketType.RANGE,
    ),
    # EXACT: "22f" or "22c"
    (
        re.compile(rf"^({_TEMP_PAT})(f|c)$"),
        BucketType.EXACT,
    ),
]


def _parse_temp(s: str) -> int:
    """Parse a temperature string, handling 'neg' prefix."""
    if s.startswith("neg"):
        return -int(s[3:].lstrip("-"))
    return int(s)


@dataclass
class ParsedBucket:
    bucket: TemperatureBucket
    raw_suffix: str


def parse_bucket_suffix(suffix: str) -> ParsedBucket | None:
    """Parse a bucket suffix from a market slug.

    Returns None if the suffix doesn't match any known pattern.
    """
    suffix = suffix.lower().strip()
    for pattern, bucket_type in BUCKET_PATTERNS:
        m = pattern.match(suffix)
        if m is None:
            continue

        groups = m.groups()
        if bucket_type == BucketType.RANGE:
            low = _parse_temp(groups[0])
            high = _parse_temp(groups[1])
            unit_str = groups[2]
        elif bucket_type in (BucketType.OR_HIGHER, BucketType.OR_BELOW):
            temp = _parse_temp(groups[0])
            low = temp
            high = temp
            unit_str = groups[1]
        else:  # EXACT
            temp = _parse_temp(groups[0])
            low = temp
            high = temp
            unit_str = groups[1]

        unit = (
            TemperatureUnit.CELSIUS if unit_str == "c"
            else TemperatureUnit.FAHRENHEIT
        )

        return ParsedBucket(
            bucket=TemperatureBucket(
                bucket_type=bucket_type,
                low=low,
                high=high,
                unit=unit,
            ),
            raw_suffix=suffix,
        )
    return None


def build_event_slug(city_slug: str, year: int, month: int, day: int) -> str:
    """Build a deterministic event slug for a city and date."""
    month_name = MONTH_NAMES[month]
    return (
        f"highest-temperature-in-{city_slug}-on-"
        f"{month_name}-{day}-{year}"
    )


@dataclass
class ParsedEventSlug:
    city_slug: str
    year: int
    month: int
    day: int


_EVENT_SLUG_RE = re.compile(
    r"^highest-temperature-in-(\w+)-on-(\w+)-(\d+)-(\d+)$"
)

_MONTH_TO_NUM = {v: k for k, v in MONTH_NAMES.items()}


def parse_event_slug(slug: str) -> ParsedEventSlug | None:
    """Parse city and date from an event slug."""
    m = _EVENT_SLUG_RE.match(slug.lower())
    if m is None:
        return None
    city = m.group(1)
    month_name = m.group(2)
    day = int(m.group(3))
    year = int(m.group(4))
    month = _MONTH_TO_NUM.get(month_name)
    if month is None:
        return None
    return ParsedEventSlug(city_slug=city, year=year, month=month, day=day)
