"""Output formatters for run summaries."""

import json

from engine.models.reporting import RunSummary


def format_summary_text(s: RunSummary) -> str:
    """Plain text summary for logging."""
    lines = [
        f"=== Scan Complete ({s.mode}) | Run {s.run_id[:8]} ===",
        f"Scanned: {s.cities_scanned} cities, {s.events_found} events, "
        f"{s.buckets_analyzed} buckets",
        f"Opportunities: {s.opportunities_found} found, "
        f"{s.blocked_count} blocked",
        f"Orders: {s.orders_attempted} attempted, "
        f"{s.orders_succeeded} succeeded, {s.orders_failed} failed",
    ]
    if s.best_edge > 0:
        lines.append(f"Best edge: +{s.best_edge:.3f} ({s.best_edge_label})")
    lines.append(
        f"Exposure: ${s.total_exposure_usd:.2f} | "
        f"Daily P&L: ${s.daily_pnl_usd:+.2f}"
    )
    if s.errors:
        lines.append(f"Errors: {len(s.errors)}")
    lines.append(f"Duration: {s.duration_seconds:.1f}s")
    return "\n".join(lines)


def format_summary_json(s: RunSummary) -> str:
    """JSON summary for programmatic consumption."""
    data = {
        "run_id": s.run_id,
        "mode": s.mode,
        "cities_scanned": s.cities_scanned,
        "events_found": s.events_found,
        "buckets_analyzed": s.buckets_analyzed,
        "opportunities_found": s.opportunities_found,
        "blocked_count": s.blocked_count,
        "block_reasons": s.block_reasons,
        "orders_attempted": s.orders_attempted,
        "orders_succeeded": s.orders_succeeded,
        "orders_failed": s.orders_failed,
        "best_edge": s.best_edge,
        "best_edge_label": s.best_edge_label,
        "total_exposure_usd": s.total_exposure_usd,
        "daily_pnl_usd": s.daily_pnl_usd,
        "duration_seconds": s.duration_seconds,
        "errors": s.errors,
    }
    return json.dumps(data, indent=2)


def format_summary_chat(s: RunSummary) -> str:
    """Chat-friendly markdown summary for OpenClaw."""
    lines = [
        f"**Scan Complete** ({s.mode}) | Run {s.run_id[:8]}",
        f"- Scanned: {s.cities_scanned} cities, {s.events_found} events, "
        f"{s.buckets_analyzed} buckets",
    ]
    block_detail = ""
    if s.blocked_count > 0:
        reasons = ", ".join(
            f"{v} {k}" for k, v in s.block_reasons.items()
        )
        block_detail = f", {s.blocked_count} blocked ({reasons})"
    lines.append(
        f"- Opportunities: {s.opportunities_found} found{block_detail}"
    )
    lines.append(
        f"- Orders: {s.orders_attempted} {s.mode}, "
        f"{s.orders_succeeded} succeeded"
    )
    if s.best_edge > 0:
        lines.append(f"- Best edge: +{s.best_edge:.3f} ({s.best_edge_label})")
    lines.append(
        f"- Exposure: ${s.total_exposure_usd:.2f} | "
        f"Daily P&L: ${s.daily_pnl_usd:+.2f}"
    )
    return "\n".join(lines)
