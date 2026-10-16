#!/usr/bin/env python3
"""Read-only structural inspection of a FLIN SQLite export.

Passing this check does not establish data safety, provenance, or mathematical
correctness. Review untrusted database files in an isolated environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

REQUIRED_COLUMNS = {
    "units": {"id", "label", "kind"},
    "edges": {"src", "dst", "kind", "weight"},
}
OPTIONAL_TABLES = ("abc_units", "abc_edges", "abc_ssrs", "theories", "papers", "relation_evidence")


def inspect(path: Path, *, require_flin: bool = False) -> dict:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Expected a regular .sqlite3 file")
    if path.suffix.lower() not in (".sqlite3", ".sqlite", ".db"):
        raise ValueError("Expected a SQLite file extension")
    with path.open("rb") as src:
        if src.read(16) != b"SQLite format 3\x00":
            raise ValueError("Not a SQLite database (invalid header)")
        digest = hashlib.sha256()
        src.seek(0)
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("PRAGMA busy_timeout=10000")
        result = con.execute("PRAGMA quick_check(1)").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"SQLite quick_check failed: {result}")
        tables = {name for (name,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for table, required in REQUIRED_COLUMNS.items():
            if table not in tables:
                raise ValueError(f"Missing required table: {table}")
            columns = {row[1] for row in con.execute(f'PRAGMA table_info("{table}")')}
            if not required.issubset(columns):
                raise ValueError(f"Incompatible {table} columns: {sorted(required - columns)}")
        counts = {table: con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                  for table in (*REQUIRED_COLUMNS, *OPTIONAL_TABLES) if table in tables}
        if require_flin:
            needed = {"abc_units", "abc_edges", "abc_meta"}
            if not needed.issubset(tables):
                raise ValueError("This SQLite file has no complete FLIN associative graph")
            enabled = con.execute(
                "SELECT value FROM abc_meta WHERE key='enabled'").fetchone()
            active = con.execute(
                "SELECT COUNT(*) FROM abc_units WHERE status='active'").fetchone()[0]
            edges = counts["abc_edges"]
            if not enabled or enabled[0] != '1':
                raise ValueError("FLIN associative network is not enabled in this snapshot")
            if not active or not edges:
                raise ValueError("A reusable FLIN snapshot needs active memory units and directed links")
            valid_edge = con.execute("""SELECT 1 FROM abc_edges e
                INNER JOIN abc_units a ON a.id=e.src AND a.status='active'
                INNER JOIN abc_units b ON b.id=e.dst AND b.status='active'
                WHERE e.weight>0 LIMIT 1""").fetchone()
            if not valid_edge:
                raise ValueError("No usable positive directed FLIN link between active units")
        return {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
            "sqlite_quick_check": "ok",
            "counts": counts,
            "disclaimer": "Structural checks only. Not a safety, licensing, provenance or scientific-validity audit.",
        }
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite_file", type=Path)
    parser.add_argument("--require-flin", action="store_true",
                        help="Require an enabled FLIN associative graph with active units and usable directed links; recommended before publishing as a FLIN network.")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.sqlite_file, require_flin=args.require_flin), indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Snapshot validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
