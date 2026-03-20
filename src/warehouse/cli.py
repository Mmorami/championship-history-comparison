from __future__ import annotations

import argparse
import csv
from pathlib import Path

from warehouse.analytics import build_views, run_ranking_snapshot, write_api_payloads
from warehouse.api_server import serve
from warehouse.config import get_settings
from warehouse.context import load_manager_record, load_player_stat
from warehouse.db import connect
from warehouse.migrations import apply_migrations
from warehouse.operations import write_health_snapshot
from warehouse.pipeline import backfill_core
from warehouse.quality import publish_quality_report
from warehouse.reconcile import write_backfill_coverage, write_reconciliation_summary


def _seed_context(conn) -> None:
    # Example seed records to validate end-to-end context pipeline.
    load_manager_record(
        conn,
        season_id="2023-24",
        team_name="Leicester City",
        manager_name="Enzo Maresca",
        from_date="2023-06-16",
        to_date="2024-06-03",
        is_primary_manager=True,
        source_confidence="A",
    )
    load_player_stat(
        conn,
        season_id="2023-24",
        team_name="Leicester City",
        player_name="Jamie Vardy",
        appearances=35,
        goals=18,
        assists=2,
        is_team_top_scorer=True,
        source_confidence="A",
        assists_coverage_complete_for_season=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Championship history warehouse CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate")

    backfill = sub.add_parser("backfill")
    backfill.add_argument("--start-season", required=True)
    backfill.add_argument("--end-season", required=True)
    backfill.add_argument("--use-network", action="store_true")

    sub.add_parser("load-context")
    pilot = sub.add_parser("pilot-ingestion")
    pilot.add_argument("--use-network", action="store_true")
    sub.add_parser("build-views")
    sub.add_parser("quality-report")
    sub.add_parser("health-snapshot")
    recon = sub.add_parser("reconcile-report")
    recon.add_argument("--start-season", required=True)
    recon.add_argument("--end-season", required=True)
    serve_cmd = sub.add_parser("serve")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8080)

    mgr_cmd = sub.add_parser(
        "import-managers",
        help="Bulk-import manager records from a CSV file (see docs/managers_template.csv).",
    )
    mgr_cmd.add_argument("--csv", required=True, help="Path to the managers CSV file.")

    scorer_cmd = sub.add_parser(
        "import-scorers",
        help="Bulk-import top-scorer records from a CSV file (see docs/scorers_template.csv).",
    )
    scorer_cmd.add_argument("--csv", required=True, help="Path to the scorers CSV file.")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    conn = connect(settings.db_path)

    if args.command == "migrate":
        apply_migrations(conn, Path("./migrations"))
        return
    if args.command == "backfill":
        backfill_core(
            conn,
            settings.raw_data_dir,
            args.start_season,
            args.end_season,
            use_network=args.use_network,
        )
        return
    if args.command == "load-context":
        _seed_context(conn)
        return
    if args.command == "pilot-ingestion":
        for season_id in ("1992-93", "2013-14", "2023-24"):
            backfill_core(
                conn,
                settings.raw_data_dir,
                season_id,
                season_id,
                use_network=args.use_network,
            )
        return
    if args.command == "build-views":
        build_views(conn)
        run_id = run_ranking_snapshot(conn, scoring_version=settings.scoring_version)
        write_api_payloads(conn, settings.reports_dir, run_id)
        return
    if args.command == "quality-report":
        report = publish_quality_report(conn, settings.reports_dir)
        print(f"Wrote report: {report}")
        return
    if args.command == "health-snapshot":
        report = write_health_snapshot(conn, settings.reports_dir)
        print(f"Wrote health snapshot: {report}")
        return
    if args.command == "reconcile-report":
        coverage = write_backfill_coverage(conn, settings.reports_dir, args.start_season, args.end_season)
        recon = write_reconciliation_summary(conn, settings.reports_dir, args.start_season, args.end_season)
        print(f"Wrote backfill coverage: {coverage}")
        print(f"Wrote reconciliation summary: {recon}")
        return
    if args.command == "serve":
        serve(settings.db_path, host=args.host, port=args.port)
        return
    if args.command == "import-managers":
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"ERROR: CSV file not found: {csv_path}")
            return
        count = 0
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                load_manager_record(
                    conn,
                    season_id=row["season_id"].strip(),
                    team_name=row["team_name"].strip(),
                    manager_name=row["manager_name"].strip(),
                    from_date=row.get("from_date", "").strip() or None,
                    to_date=row.get("to_date", "").strip() or None,
                    is_primary_manager=row.get("is_primary_manager", "1").strip() == "1",
                    source_confidence=row.get("source_confidence", "B").strip() or "B",
                )
                count += 1
        print(f"Imported {count} manager record(s) from {csv_path}")
        return
    if args.command == "import-scorers":
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"ERROR: CSV file not found: {csv_path}")
            return
        count = 0
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                goals_str = row.get("goals", "").strip()
                assists_str = row.get("assists", "").strip()
                appearances_str = row.get("appearances", "").strip()
                load_player_stat(
                    conn,
                    season_id=row["season_id"].strip(),
                    team_name=row["team_name"].strip(),
                    player_name=row["player_name"].strip(),
                    appearances=int(appearances_str) if appearances_str else None,
                    goals=int(goals_str) if goals_str else None,
                    assists=int(assists_str) if assists_str else None,
                    is_team_top_scorer=row.get("is_team_top_scorer", "1").strip() == "1",
                    source_confidence=row.get("source_confidence", "B").strip() or "B",
                    assists_coverage_complete_for_season=row.get("assists_coverage_complete_for_season", "0").strip() == "1",
                )
                count += 1
        print(f"Imported {count} top-scorer record(s) from {csv_path}")
        return


if __name__ == "__main__":
    main()

