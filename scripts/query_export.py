#!/usr/bin/env python3
"""One-shot: execute SQL via db_query API and export results to CSV/JSON.

Example:
  python scripts/query_export.py \\
    --db postgres \\
    --sql "SELECT current_database() AS db, now() AS ts" \\
    --format csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def api_request(method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else None


def build_filename(db: str, fmt: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{db}_{stamp}.{fmt}"


def write_csv(path: Path, columns: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    headers = [c["name"] for c in columns]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query db_query API and export results")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--db", required=True, help="Registered connection name")
    parser.add_argument("--sql", default=None, help="SQL SELECT to execute")
    parser.add_argument("--sql-file", default=None, help="Read SQL from file")
    parser.add_argument("--format", choices=("csv", "json"), default="csv")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "exports"),
        help="Output directory",
    )
    args = parser.parse_args()

    if not args.sql and not args.sql_file:
        parser.error("Provide --sql or --sql-file")
    sql = args.sql
    if args.sql_file:
        sql = Path(args.sql_file).read_text(encoding="utf-8")

    base = args.base_url.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        health = api_request("GET", f"{base}/health")
        if not health or health.get("status") != "healthy":
            print(f"ERROR backend unhealthy: {health}", file=sys.stderr)
            return 1

        result = api_request(
            "POST",
            f"{base}/api/v1/dbs/{args.db}/query",
            {"sql": sql.strip()},
        )
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"ERROR HTTP {e.code}: {detail}", file=sys.stderr)
        return 1
    except URLError as e:
        print(f"ERROR cannot reach backend at {base}: {e}", file=sys.stderr)
        return 1

    columns = result.get("columns") or []
    rows = result.get("rows") or []
    row_count = result.get("rowCount", len(rows))
    elapsed = result.get("executionTimeMs")

    filename = build_filename(args.db, args.format)
    path = out_dir / filename
    if args.format == "csv":
        write_csv(path, columns, rows)
    else:
        write_json(path, rows)

    print(
        f"OK rows={row_count} time_ms={elapsed} file={path.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
