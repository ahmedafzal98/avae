#!/usr/bin/env python3
"""
Add prompt and summary columns to documents table

Fixes: ERROR: column documents.prompt does not exist

Usage:
    python3 migrations/run_migration_002.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import engine
from sqlalchemy import text

def run():
    print("=" * 60)
    print("Adding prompt and summary columns to documents table")
    print("=" * 60)
    
    with engine.connect() as conn:
        for col in ["prompt", "summary"]:
            try:
                conn.execute(text(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {col} TEXT"))
                conn.commit()
                print(f"  Added column: {col}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  Column {col} already exists (skipping)")
                else:
                    raise
    print("Done.")

if __name__ == "__main__":
    run()
