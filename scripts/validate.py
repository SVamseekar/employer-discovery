# scripts/validate.py
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN

MASTER_PATH = "data/master_employers.csv"

def load_master():
    if not os.path.exists(MASTER_PATH):
        return []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def domain_from_website(website: str) -> str:
    """Extract bare domain for deduplication."""
    if not website or website == UNKNOWN:
        return ""
    url = website.lower().strip()
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0].strip()

def append_batch(batch_path: str):
    """Append a batch CSV to master, deduplicating by Company name (case-insensitive)."""
    existing = load_master()
    existing_names = {r["Company"].lower().strip() for r in existing}
    existing_domains = {domain_from_website(r["Website"]) for r in existing if domain_from_website(r["Website"])}

    with open(batch_path, newline="", encoding="utf-8") as f:
        batch = list(csv.DictReader(f))

    added = 0
    skipped = 0
    new_rows = []

    for row in batch:
        name_key = row.get("Company", "").lower().strip()
        domain_key = domain_from_website(row.get("Website", ""))

        if name_key in existing_names:
            skipped += 1
            continue
        if domain_key and domain_key in existing_domains:
            skipped += 1
            continue

        # Ensure all 24 fields present
        for field in FIELDS:
            if field not in row:
                row[field] = UNKNOWN

        new_rows.append(row)
        existing_names.add(name_key)
        if domain_key:
            existing_domains.add(domain_key)
        added += 1

    all_rows = existing + new_rows
    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Batch {batch_path}: +{added} added, {skipped} skipped (duplicates). Total: {len(all_rows)}")

def stats():
    rows = load_master()
    countries = {}
    stages = {}
    for r in rows:
        countries[r["Country"]] = countries.get(r["Country"], 0) + 1
        stages[r["Company_Stage"]] = stages.get(r["Company_Stage"], 0) + 1
    print(f"\nTotal employers: {len(rows)}")
    print("\nBy Country:")
    for k, v in sorted(countries.items(), key=lambda x: -x[1])[:15]:
        print(f"  {k}: {v}")
    print("\nBy Stage:")
    for k, v in sorted(stages.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

def export_cold_outreach(output_path="data/cold_outreach_shortlist.csv"):
    """Export all companies flagged as Cold_Outreach_Candidate = Yes."""
    rows = load_master()
    shortlist = [r for r in rows if r.get("Cold_Outreach_Candidate", "").strip() == "Yes"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(shortlist)
    print(f"Cold outreach shortlist: {len(shortlist)} companies → {output_path}")

if __name__ == "__main__":
    stats()
