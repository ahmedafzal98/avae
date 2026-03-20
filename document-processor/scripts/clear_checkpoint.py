#!/usr/bin/env python3
"""
Clear LangGraph checkpoint data for a thread_id.

Use when a task fails with "Channel names checkpoint_id are reserved" due to
stale/corrupt checkpoint data in Postgres. Clearing allows the task to run fresh.

Usage:
  python scripts/clear_checkpoint.py 23
  python scripts/clear_checkpoint.py 23 --dry-run
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Clear LangGraph checkpoint data for a thread_id")
    parser.add_argument("thread_id", help="Thread ID (task_id) to clear, e.g. 23")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    thread_id = args.thread_id.strip()
    if not thread_id:
        print("Error: thread_id is required", file=sys.stderr)
        sys.exit(1)

    try:
        from app.graph.checkpointer import get_checkpointer
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    checkpointer = get_checkpointer()
    if checkpointer is None:
        print("Error: Postgres checkpointer not available (psycopg required)", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Would clear checkpoint data for thread_id={thread_id}")
        print("Run without --dry-run to actually delete.")
        return 0

    try:
        checkpointer.delete_thread(thread_id)
        print(f"Cleared checkpoint data for thread_id={thread_id}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
