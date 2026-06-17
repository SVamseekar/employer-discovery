# scripts/validate.py
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from record_classifier import classify_record, website_domain
from schema import FIELDS, JOB_SIGNAL_FIELDS, UNKNOWN, row_to_job_signal

BASE = os.path.join(os.path.dirname(__file__), "..")
MASTER_PATH = os.path.normpath(os.path.join(BASE, "data", "master_employers.csv"))
JOB_SIGNALS_PATH = os.path.normpath(os.path.join(BASE, "data", "job_signals.csv"))


def _load_csv(path: str, fields: list[str]) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, fields: list[str], rows: list[dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, UNKNOWN) for k in fields})


def load_master():
    return _load_csv(MASTER_PATH, FIELDS)


def load_job_signals():
    return _load_csv(JOB_SIGNALS_PATH, JOB_SIGNAL_FIELDS)


def append_batch(batch_path: str):
    """Route batch rows to master_employers or job_signals — never drop sources."""
    companies = load_master()
    signals = load_job_signals()

    company_names = {r["Company"].lower().strip() for r in companies}
    company_domains = {website_domain(r.get("Website", "")) for r in companies if website_domain(r.get("Website", ""))}
    signal_keys = {
        (r["Company"].lower().strip(), (r.get("Job_URL") or "").lower().strip())
        for r in signals
    }

    with open(batch_path, newline="", encoding="utf-8") as f:
        batch = list(csv.DictReader(f))

    added_companies = added_signals = 0
    skipped = 0

    for row in batch:
        for field in FIELDS:
            if field not in row:
                row[field] = UNKNOWN

        kind = classify_record(row)
        name_key = row.get("Company", "").lower().strip()
        if not name_key:
            skipped += 1
            continue

        if kind == "job_signal":
            job_url = (row.get("Careers_URL") or "").strip()
            sig_key = (name_key, job_url.lower())
            if sig_key in signal_keys:
                skipped += 1
                continue
            signals.append(row_to_job_signal(row))
            signal_keys.add(sig_key)
            added_signals += 1
            continue

        domain_key = website_domain(row.get("Website", ""))
        if name_key in company_names:
            skipped += 1
            continue
        if domain_key and domain_key in company_domains:
            skipped += 1
            continue

        companies.append(row)
        company_names.add(name_key)
        if domain_key:
            company_domains.add(domain_key)
        added_companies += 1

    _write_csv(MASTER_PATH, FIELDS, companies)
    _write_csv(JOB_SIGNALS_PATH, JOB_SIGNAL_FIELDS, signals)

    print(
        f"Batch {batch_path}: +{added_companies} companies, +{added_signals} job signals, "
        f"{skipped} skipped. Totals: {len(companies)} companies, {len(signals)} signals"
    )
    return added_companies + added_signals


def stats():
    companies = load_master()
    signals = load_job_signals()
    countries = {}
    for r in companies:
        countries[r["Country"]] = countries.get(r["Country"], 0) + 1
    print(f"\nCompanies: {len(companies)}")
    print(f"Job signals: {len(signals)}")
    print("\nCompanies by country (top 15):")
    for k, v in sorted(countries.items(), key=lambda x: -x[1])[:15]:
        print(f"  {k}: {v}")


def export_cold_outreach(output_path="data/cold_outreach_shortlist.csv"):
    rows = load_master()
    shortlist = [r for r in rows if r.get("Cold_Outreach_Candidate", "").strip() == "Yes"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(shortlist)
    print(f"Cold outreach shortlist: {len(shortlist)} companies → {output_path}")


if __name__ == "__main__":
    stats()