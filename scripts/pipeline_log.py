# scripts/pipeline_log.py
"""
Appends a run log entry to data/pipeline_log.csv.
Usage: python scripts/pipeline_log.py "Source Name" 42 "optional notes"
"""
import csv
import os
import sys
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pipeline_log.csv")
LOG_FIELDS = ["Run_Date", "Source", "Companies_Added", "Notes"]


def log_run(source: str, companies_added: int, notes: str = ""):
    log_path = os.path.normpath(LOG_PATH)
    file_exists = os.path.exists(log_path)

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "Run_Date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "Source": source,
            "Companies_Added": str(companies_added),
            "Notes": notes,
        })

    print(f"Logged: {source} +{companies_added} companies")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    added = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    notes = sys.argv[3] if len(sys.argv) > 3 else ""
    log_run(source, added, notes)
