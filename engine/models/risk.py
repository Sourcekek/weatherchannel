"""Risk check models."""

from dataclasses import dataclass
from enum import StrEnum


class BlockReason(StrEnum):
    KILL_SWITCH = "KILL_SWITCH"
    PAUSED = "PAUSED"
    POSITION_SIZE = "POSITION_SIZE"
    TRADES_PER_RUN = "TRADES_PER_RUN"
    TOTAL_EXPOSURE = "TOTAL_EXPOSURE"
    PER_CITY_EXPOSURE = "PER_CITY_EXPOSURE"
    DAILY_LOSS = "DAILY_LOSS"
    COOLDOWN = "COOLDOWN"
    TIME_TO_RESOLUTION = "TIME_TO_RESOLUTION"
    SLIPPAGE = "SLIPPAGE"


@dataclass(frozen=True)
class RiskCheckResult:
    check_name: str
    passed: bool
    block_reason: BlockReason | None
    detail: str


@dataclass(frozen=True)
class RiskVerdict:
    approved: bool
    checks: list[RiskCheckResult]

    @property
    def block_reasons(self) -> list[BlockReason]:
        return [c.block_reason for c in self.checks if c.block_reason is not None]
