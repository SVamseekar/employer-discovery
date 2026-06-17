#!/usr/bin/env python3
"""
One-time (re-runnable) split of mixed master_employers.csv into:
  - data/master_employers.csv  (real companies)
  - data/job_signals.csv       (Indeed/LinkedIn/Seek/etc. listings)

Preserves every row — nothing deleted.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from record_classifier import classify_record
from schema import FIELDS, JOB_SIGNAL_FIELDS, UNKNOWN, row_to_job_signal

BASE = os.path.join(os.path.dirname(__file__), "..")
MASTER = os.path.join(BASE, "data", "master_employers.csv")
BACKUP = os.path.join(BASE, "data", "master_employers_backup.csv")
SIGNALS = os.path.join(BASE, "data", "job_signals.csv")


def main():
    if not os.path.exists(MASTER):
        print(f"Missing {MASTER}")
        return 1

    with open(MASTER, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not os.path.exists(BACKUP):
        with open(BACKUP, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(f"Backup → {BACKUP}")

    companies, signals = [], []
    seen_co, seen_sig = set(), set()

    for row in rows:
        for field in FIELDS:
            row.setdefault(field, UNKNOWN)
        kind = classify_record(row)
        if kind == "job_signal":
            sig = row_to_job_signal(row)
            key = (sig["Company"].lower(), sig["Job_URL"].lower())
            if key not in seen_sig:
                signals.append(sig)
                seen_sig.add(key)
        else:
            key = row["Company"].lower().strip()
            if key not in seen_co:
                companies.append(row)
                seen_co.add(key)

    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(companies)

    with open(SIGNALS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=JOB_SIGNAL_FIELDS)
        w.writeheader()
        w.writerows(signals)

    print(f"Split complete: {len(companies)} companies, {len(signals)} job signals")
    print(f"  {MASTER}")
    print(f"  {SIGNALS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())