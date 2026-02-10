"""Tests for edge calculator: positive/negative edge, boundaries, fees."""

from engine.models.signal import ReasonCode
from engine.signal.edge_calculator import compute_edge


def _edge(**kwargs):
    defaults = {
        "run_id": "run1",
        "event_id": "e1",
        "market_id": "m1",
        "city_slug": "nyc",
        "target_date": "2026-02-11",
        "bucket_label": "36-37F",
        "bucket_probability": 0.26,
        "market_price_yes": 0.075,
        "fee_estimate": 0.02,
        "slippage_estimate": 0.01,
        "sigma_used": 2.5,
        "min_edge_threshold": 0.05,
        "max_entry_price": 0.15,
        "accepting_orders": True,
        "liquidity": 100.0,
    }
    defaults.update(kwargs)
    return compute_edge(**defaults)


class TestComputeEdge:
    def test_positive_edge_opportunity(self):
        er = _edge(bucket_probability=0.26, market_price_yes=0.075)
        assert er.reason_code == ReasonCode.OPPORTUNITY
        assert er.gross_edge > 0
        assert er.net_edge > 0.05

    def test_negative_edge(self):
        er = _edge(bucket_probability=0.05, market_price_yes=0.10)
        assert er.reason_code == ReasonCode.NEGATIVE_EDGE
        assert er.net_edge < 0

    def test_edge_below_threshold(self):
        er = _edge(
            bucket_probability=0.13, market_price_yes=0.075,
            fee_estimate=0.02, slippage_estimate=0.01
        )
        # net_edge = 0.13 - 0.075 - 0.02 - 0.01 = 0.025 < 0.05
        assert er.reason_code == ReasonCode.EDGE_BELOW_THRESHOLD

    def test_price_above_max_entry(self):
        er = _edge(market_price_yes=0.20, max_entry_price=0.15)
        assert er.reason_code == ReasonCode.PRICE_ABOVE_MAX_ENTRY

    def test_not_accepting_orders(self):
        er = _edge(accepting_orders=False)
        assert er.reason_code == ReasonCode.NOT_ACCEPTING_ORDERS

    def test_zero_liquidity(self):
        er = _edge(liquidity=0.0)
        assert er.reason_code == ReasonCode.ZERO_LIQUIDITY

    def test_fees_exceed_gross_edge(self):
        er = _edge(
            bucket_probability=0.10, market_price_yes=0.075,
            fee_estimate=0.05, slippage_estimate=0.05
        )
        assert er.net_edge < 0
        assert er.reason_code == ReasonCode.NEGATIVE_EDGE

    def test_edge_fields_correct(self):
        er = _edge(
            bucket_probability=0.30, market_price_yes=0.05,
            fee_estimate=0.02, slippage_estimate=0.01
        )
        assert er.gross_edge == 0.30 - 0.05
        assert er.net_edge == 0.30 - 0.05 - 0.02 - 0.01
