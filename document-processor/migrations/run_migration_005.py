#!/usr/bin/env python3
"""
Add retry_count column and reconciliation index to documents table (Issue #10)

Usage:
    python3 migrations/run_migration_005.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine
from sqlalchemy import text


def run():
    print("=" * 60)
    print("Adding retry_count column + reconciliation index to documents table")
    print("=" * 60)

    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0"
        ))
        conn.commit()
        print("  Added column: retry_count")

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_documents_reconciliation "
            "ON documents (status, created_at, retry_count)"
        ))
        conn.commit()
        print("  Added index: idx_documents_reconciliation")

    print("Done.")


if __name__ == "__main__":
    run()
