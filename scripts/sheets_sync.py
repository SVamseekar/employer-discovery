# scripts/sheets_sync.py
"""
Deduplicates master_employers.csv by Company name (case-insensitive).
Run after any pipeline batch to keep the master file clean.
Usage: python scripts/sheets_sync.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN

MASTER_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "master_employers.csv")


def dedup_master():
    master_path = os.path.normpath(MASTER_PATH)
    if not os.path.exists(master_path):
        print(f"Master file not found: {master_path}")
        return

    with open(master_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    seen = set()
    unique = []
    dupes = 0

    for row in rows:
        key = row.get("Company", "").lower().strip()
        if not key or key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(row)

    with open(master_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(unique)

    print(f"Dedup complete: {len(unique)} unique, {dupes} removed. Total: {len(unique)}")


if __name__ == "__main__":
    dedup_master()
