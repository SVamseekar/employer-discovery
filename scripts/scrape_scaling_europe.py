"""
Scrape Scaling Europe daily newsletter (Seb Johnson) for EU startup names.
Only processes posts published since last run — tracks seen posts in a state file.
"""
import re, requests, csv, os, json
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), "..")

import sys
sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run

BATCH_DIR = os.path.join(BASE, "batches")
STATE_FILE = os.path.join(BASE, "data", "scaling_europe_seen.json")


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def get_post_links():
    r = requests.get("https://scalingeurope.substack.com/feed", timeout=15)
    links = re.findall(r'<link>(https://scalingeurope\.substack\.com/p/[^<]+)</link>', r.text)
    return links  # all available posts


def extract_companies_from_post(url):
    """Extract bolded/linked company names from a post."""
    r = requests.get(url, timeout=15,
                     headers={"User-Agent": "Mozilla/5.0"})
    html = r.text

    companies = []

    # Pattern 1: "London-based CompanyName raised" or "Berlin-based CompanyName"
    city_pattern = re.findall(
        r'(?:London|Berlin|Paris|Amsterdam|Stockholm|Dublin|Munich|Madrid|Barcelona|'
        r'Warsaw|Lisbon|Prague|Helsinki|Vienna|Zurich|Brussels|Copenhagen|Oslo|'
        r'Milan|Rome|Budapest|Bucharest|Ghent|UK|German|French|Dutch|Swedish|'
        r'European?)-based\s+([A-Z][A-Za-z0-9\s\.\-]+?)(?:\s+raised|\s+launches|\s+closes|'
        r'\s+files|\s+expands|\s+announces|\s+builds|\s+targets)',
        html
    )
    companies.extend(city_pattern)

    # Pattern 2: Bold company names <strong>CompanyName</strong>
    bold = re.findall(r'<strong[^>]*>([A-Z][A-Za-z0-9\s\.\-]{2,40}?)</strong>', html)
    companies.extend(bold)

    # Clean up
    seen = set()
    result = []
    for c in companies:
        c = c.strip().strip('"\'').strip()
        if len(c) < 2 or len(c) > 50:
            continue
        if c.lower() in ("the", "and", "for", "with", "from", "read more", "here"):
            continue
        if c not in seen:
            seen.add(c)
            result.append(c)

    return result


def row(**kwargs):
    r = {f: UNKNOWN for f in FIELDS}
    r.update(kwargs)
    return r


def run():
    print("Scraping Scaling Europe (Seb Johnson)...")
    links = get_post_links()
    seen_posts = load_seen()

    new_links = [l for l in links if l not in seen_posts]
    print(f"  Found {len(links)} posts, {len(new_links)} new since last run")

    all_companies = set()
    for url in new_links:
        try:
            companies = extract_companies_from_post(url)
            all_companies.update(companies)
            seen_posts.add(url)
            print(f"  {url.split('/')[-1]}: {len(companies)} companies")
        except Exception as e:
            print(f"  Error on {url}: {e}")

    save_seen(seen_posts)

    rows = []
    for company in all_companies:
        rows.append(row(
            Company=company,
            Source="Scaling Europe (Seb Johnson)",
            Country="Europe",
            Sector="Tech",
            Employer_Category="EU Startup",
            Hiring_Geography="Europe",
            Hiring_Confidence="Medium",
            Reason_Match="Featured in Scaling Europe daily newsletter",
            Language_Requirement="English",
            Remote="Unknown",
        ))

    if rows:
        path = os.path.join(BATCH_DIR, f"pipeline_scaling_europe_{datetime.now().strftime('%Y%m%d')}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        append_batch(path)

    print(f"  Scaling Europe: {len(rows)} companies extracted")
    log_run("Scaling Europe", len(rows))
    return len(rows)


if __name__ == "__main__":
    run()
