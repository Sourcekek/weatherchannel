"""Scan pipeline: full scan cycle orchestration."""

import json
import logging
import time
import uuid

from engine.config.loader import snapshot_config
from engine.config.schema import EngineConfig, ExecutionMode
from engine.execution.dry_run import DryRunAdapter
from engine.execution.executor import Executor
from engine.execution.idempotency import generate_idempotency_key
from engine.execution.live_adapter import LiveAdapter
from engine.ingest.forecast_fetcher import ForecastFetcher
from engine.ingest.gamma_client import GammaClient
from engine.ingest.market_scanner import MarketScanner
from engine.ingest.noaa_client import NoaaClient
from engine.models.execution import OrderIntent, OrderStatus
from engine.models.forecast import ForecastPoint
from engine.models.market import MarketEvent
from engine.models.reporting import RunSummary
from engine.reporting.formatters import format_summary_chat, format_summary_text
from engine.reporting.run_summarizer import RunSummarizer
from engine.risk.engine import RiskEngine
from engine.risk.state_tracker import StateTracker
from engine.signal.signal_generator import SignalGenerator
from engine.storage import (
    forecast_repo,
    market_repo,
    position_repo,
    risk_repo,
    signal_repo,
    state_repo,
)
from engine.storage.database import connect, run_migrations

logger = logging.getLogger(__name__)


class ScanPipeline:
    def __init__(self, config: EngineConfig, db_path: str = "data/engine.db"):
        self.config = config
        self.db_path = db_path

    def run(self) -> RunSummary:
        """Execute a full scan cycle."""
        start_time = time.monotonic()
        run_id = str(uuid.uuid4())

        # 1. INIT
        conn = connect(self.db_path)
        run_migrations(conn)

        # Snapshot config
        c_hash = snapshot_config(self.config, conn)
        mode = self.config.execution.mode.value

        # Record run start
        state_repo.create_run(conn, run_id, mode, c_hash)
        summarizer = RunSummarizer(run_id, mode)

        # Check system state
        if state_repo.is_kill_switch_active(conn):
            logger.warning("Kill switch active, aborting scan")
            summarizer.record_error("Kill switch active")
            summary = summarizer.finalize()
            state_repo.complete_run(conn, run_id, "aborted")
            conn.close()
            return summary

        if state_repo.is_paused(conn):
            logger.warning("System paused, aborting scan")
            summarizer.record_error("System paused")
            summary = summarizer.finalize()
            state_repo.complete_run(conn, run_id, "aborted")
            conn.close()
            return summary

        try:
            # 2. INGEST: MARKETS
            gamma = GammaClient()
            scanner = MarketScanner(self.config, gamma)
            event_results = scanner.scan()

            events: list[MarketEvent] = []
            for event, raw_json in event_results:
                market_repo.save_market_event(conn, event, raw_json)
                events.append(event)

            enabled_cities = [c for c in self.config.cities if c.enabled]
            summarizer.record_scan(len(enabled_cities), len(events))
            logger.info("Ingested %d events from %d cities", len(events), len(enabled_cities))

            # 3. INGEST: FORECASTS
            noaa = NoaaClient()
            fetcher = ForecastFetcher(noaa)
            city_map = {c.slug: c for c in self.config.cities}

            forecasts: dict[tuple[str, str], ForecastPoint] = {}
            seen_pairs: set[tuple[str, str]] = set()

            for event in events:
                pair = (event.city_slug, event.target_date)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                city_cfg = city_map.get(event.city_slug)
                if city_cfg is None:
                    continue

                fp = fetcher.fetch(city_cfg, event.target_date)
                if fp is not None:
                    forecasts[pair] = fp
                    forecast_repo.save_forecast(
                        conn,
                        fp.city_slug,
                        fp.target_date,
                        fp.high_temp_f,
                        fp.source_generated_at,
                        json.dumps([
                            {
                                "name": p.name,
                                "temperature": p.temperature,
                                "is_daytime": p.is_daytime,
                            }
                            for p in fp.raw_periods
                        ]),
                    )

            logger.info("Fetched %d forecasts", len(forecasts))

            # 4. SIGNAL GENERATION
            sig_gen = SignalGenerator(self.config, run_id)
            edge_results = sig_gen.generate(events, forecasts)

            for er in edge_results:
                signal_repo.save_edge_result(conn, er)

            summarizer.record_edge_results(edge_results)
            opportunities = sig_gen.filter_opportunities(edge_results)
            signals = sig_gen.to_signals(opportunities, events)
            logger.info(
                "Generated %d edge results, %d opportunities",
                len(edge_results), len(opportunities),
            )

            # 5. RISK + EXECUTION
            state = StateTracker(conn)
            state.hydrate()
            risk_engine = RiskEngine(self.config.risk, state)

            adapter: DryRunAdapter | LiveAdapter
            if self.config.execution.mode == ExecutionMode.LIVE:
                adapter = LiveAdapter()
            else:
                adapter = DryRunAdapter()
            executor = Executor(conn, adapter)

            # Build end_date lookup
            end_date_map: dict[str, str] = {}
            for event in events:
                for bm in event.buckets:
                    end_date_map[bm.market_id] = bm.end_date

            for signal in signals:
                end_date = end_date_map.get(signal.market_id, "")
                verdict = risk_engine.evaluate(signal, end_date)
                summarizer.record_risk_verdict(verdict)

                # Persist risk checks
                idem_key = generate_idempotency_key(
                    run_id, signal.market_id, "BUY",
                    signal.edge_result.market_price_yes,
                )
                risk_repo.save_risk_checks(
                    conn, run_id, idem_key, verdict.checks
                )

                if not verdict.approved:
                    logger.info(
                        "Blocked: %s reasons=%s",
                        signal.market_id,
                        [r.value for r in verdict.block_reasons],
                    )
                    continue

                # Create and execute order
                intent = OrderIntent(
                    run_id=run_id,
                    idempotency_key=idem_key,
                    market_id=signal.market_id,
                    clob_token_id=signal.clob_token_id_yes,
                    side="BUY",
                    price=signal.edge_result.market_price_yes,
                    size_usd=signal.proposed_size_usd,
                    city_slug=signal.edge_result.city_slug,
                    target_date=signal.edge_result.target_date,
                    bucket_label=signal.edge_result.bucket_label,
                    net_edge=signal.edge_result.net_edge,
                )

                result = executor.execute(intent)
                summarizer.record_order_result(result)

                if result.status in (OrderStatus.DRY_RUN, OrderStatus.FILLED):
                    state.record_trade(
                        signal.edge_result.city_slug,
                        signal.proposed_size_usd,
                    )
                    position_repo.save_position(
                        conn,
                        signal.market_id,
                        signal.edge_result.city_slug,
                        signal.edge_result.target_date,
                        signal.edge_result.bucket_label,
                        signal.edge_result.market_price_yes,
                        signal.proposed_size_usd,
                    )

                # Check max trades per run
                if state.trades_this_run >= self.config.risk.max_trades_per_run:
                    logger.info("Max trades per run reached, stopping")
                    break

            # 6. REPORT
            summarizer.record_exposure(
                position_repo.get_total_open_exposure(conn),
                0.0,  # PnL calculation deferred
            )
            summarizer.record_duration(time.monotonic() - start_time)
            summary = summarizer.finalize()

            # Persist run completion
            state_repo.complete_run(
                conn,
                run_id,
                "completed",
                summary_json=json.dumps({
                    "events_found": summary.events_found,
                    "opportunities": summary.opportunities_found,
                    "orders_succeeded": summary.orders_succeeded,
                }),
                events_found=summary.events_found,
                opportunities_found=summary.opportunities_found,
                orders_attempted=summary.orders_attempted,
                orders_succeeded=summary.orders_succeeded,
                best_edge=summary.best_edge,
            )

            # Output
            logger.info("\n%s", format_summary_text(summary))
            print(format_summary_chat(summary))

            return summary

        except Exception as e:
            logger.exception("Scan pipeline failed")
            summarizer.record_error(str(e))
            summarizer.record_duration(time.monotonic() - start_time)
            summary = summarizer.finalize()
            state_repo.complete_run(
                conn, run_id, "failed", error_message=str(e)
            )
            return summary

        finally:
            conn.close()
