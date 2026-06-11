"""
Naukri.com scraper — Data/AI Engineering jobs in India.

WHY THIS IS HARD:
  Naukri's main search page is JS-rendered (React) behind Cloudflare.
  Direct requests.get() gets a JS shell, not real content.
  
  Three approaches tried here in order:
    1. Naukri's internal JSON API (v2 endpoint used by their mobile app) — 
       works intermittently, no JS needed, returns structured job data.
    2. Their sitemap-derived company list — static XML, always accessible.
    3. Curated static seed — top Naukri-visible employers for Data/AI in India.
       This always runs and guarantees minimum coverage.

  If you want reliable live Naukri scraping, next step is Playwright/Selenium
  (see ISSUES_AND_CHANGES.md). This file handles everything short of that.
"""
import csv, os, requests, json, sys, time, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run

BASE    = os.path.join(os.path.dirname(__file__), "..")
MASTER  = os.path.join(BASE, "data", "master_employers.csv")
BATCHES = os.path.join(BASE, "batches")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.naukri.com/",
    "appid": "109",
    "systemid": "Naukri",
}


def row(**kwargs):
    r = {f: UNKNOWN for f in FIELDS}
    r.update(kwargs)
    return r


def write_batch(rows, name):
    os.makedirs(BATCHES, exist_ok=True)
    path = os.path.join(BATCHES, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    append_batch(path)
    return len(rows)


# ── Approach 1: Naukri internal v2 API ─────────────────────────────────────

NAUKRI_API = "https://www.naukri.com/jobapi/v3/search"

DATA_QUERIES = [
    ("data engineer", "data-engineer-jobs"),
    ("ai engineer", "ai-engineer-jobs"),
    ("ml engineer", "machine-learning-engineer-jobs"),
    ("data platform engineer", "data-platform-engineer-jobs"),
    ("analytics engineer", "analytics-engineer-jobs"),
]

def scrape_naukri_api() -> list:
    """
    Hit Naukri's internal job search API.
    Returns extracted company names as row dicts, or [] on failure.
    """
    rows = []
    seen = set()
    for keyword, nobot_id in DATA_QUERIES:
        try:
            params = {
                "noOfResults": 50,
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": keyword,
                "pageNo": 1,
                "k": keyword,
                "experience": "1",  # 1+ years
                "jobAge": 15,       # last 15 days
            }
            r = requests.get(
                NAUKRI_API, params=params, headers=HEADERS, timeout=12
            )
            if r.status_code != 200:
                print(f"    Naukri API {keyword}: HTTP {r.status_code}")
                continue

            data = r.json()
            jobs = data.get("jobDetails") or data.get("jobs") or []
            for job in jobs:
                company = (
                    job.get("companyName")
                    or job.get("company", {}).get("label")
                    or ""
                ).strip()
                title   = job.get("title", "") or ""
                jurl    = job.get("jdURL") or job.get("jobId", "")
                city    = (job.get("placeholders", [{}])[0].get("label", "") 
                           if job.get("placeholders") else "")

                if not company or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Naukri.com API",
                    Country="India",
                    City=city or UNKNOWN,
                    Sector="Tech / Data / AI",
                    Employer_Category="india tech",
                    Remote=UNKNOWN,
                    Hiring_Geography="India",
                    Target_Roles=title[:80] if title else UNKNOWN,
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring '{keyword}' on Naukri (last 15 days)",
                    Careers_URL=f"https://www.naukri.com/{jurl}" if jurl else UNKNOWN,
                    Language_Requirement="English",
                ))
            time.sleep(1.5)
        except Exception as e:
            print(f"    Naukri API '{keyword}' failed: {e}")
    return rows


# ── Approach 2: Naukri company sitemap ─────────────────────────────────────

SITEMAP_URL = "https://www.naukri.com/sitemap-company-jobs.xml"

def scrape_naukri_sitemap() -> list:
    """
    Naukri publishes a company-level sitemap — plain XML, no JS.
    Extracts company slugs → infers company names.
    """
    rows = []
    seen = set()
    try:
        r = requests.get(SITEMAP_URL, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=15)
        if r.status_code != 200:
            print(f"    Naukri sitemap: HTTP {r.status_code}")
            return []
        # Extract company slugs from URLs like /company-name-jobs-N
        slugs = re.findall(r'/([a-z0-9-]+-jobs-\d+)', r.text)
        for slug in slugs[:300]:  # cap at 300 to avoid noise
            name_raw = re.sub(r'-jobs-\d+$', '', slug)
            name = name_raw.replace("-", " ").title()
            if not name or name in seen or len(name) < 3:
                continue
            seen.add(name)
            rows.append(row(
                Company=name,
                Source="Naukri.com Sitemap",
                Country="India",
                Sector="Tech",
                Employer_Category="india tech",
                Hiring_Geography="India",
                Hiring_Confidence="Low",
                Reason_Match="Listed as hiring company on Naukri sitemap",
                Careers_URL=f"https://www.naukri.com/{slug}",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"    Naukri sitemap failed: {e}")
    return rows


# ── Approach 3: Curated static seed ────────────────────────────────────────
# Top Indian companies known to post Data/AI Engineering roles on Naukri.
# This list is verified by direct Naukri search and never becomes stale
# for the major employers.

NAUKRI_SEED = [
    # MNC GCCs heavily active on Naukri
    ("Accenture", "accenture.com", "Hyderabad/Bangalore/Mumbai"),
    ("Capgemini", "capgemini.com", "Hyderabad/Bangalore/Pune"),
    ("IBM India", "ibm.com", "Hyderabad/Bangalore/Mumbai"),
    ("Deloitte India", "deloitte.com", "Hyderabad/Bangalore/Mumbai"),
    ("PwC India", "pwc.com", "Hyderabad/Bangalore/Mumbai"),
    ("EY India", "ey.com", "Hyderabad/Bangalore/Mumbai"),
    ("KPMG India", "kpmg.com/in", "Bangalore/Mumbai"),
    ("Cognizant", "cognizant.com", "Hyderabad/Chennai/Bangalore"),
    ("Capgemini Engineering", "capgemini.com", "Hyderabad/Bangalore"),
    ("Mindtree", "mindtree.com", "Bangalore"),
    ("Mphasis", "mphasis.com", "Bangalore"),

    # Indian product & analytics companies on Naukri
    ("Mu Sigma", "mu-sigma.com", "Bangalore"),
    ("Fractal Analytics", "fractal.ai", "Mumbai/Bangalore/Hyderabad"),
    ("Tiger Analytics", "tigeranalytics.com", "Chennai/Bangalore"),
    ("LatentView Analytics", "latentview.com", "Chennai"),
    ("ThoughtWorks", "thoughtworks.com", "Bangalore/Hyderabad"),
    ("Sigmoid Analytics", "sigmoid.com", "Bangalore"),
    ("Quantiphi", "quantiphi.com", "Mumbai/Bangalore"),
    ("MathCo", "themathcompany.com", "Bangalore"),
    ("Incedo", "incedoinc.com", "Gurugram"),
    ("EXL Service", "exlservice.com", "Noida/Hyderabad"),
    ("WNS Analytics", "wns.com", "Mumbai/Bangalore"),
    ("Innover Analytics", "innoverdigital.com", "Hyderabad"),

    # Fast-growing Indian unicorns active on Naukri
    ("PhonePe", "phonepe.com", "Bangalore"),
    ("Razorpay", "razorpay.com", "Bangalore"),
    ("Meesho", "meesho.com", "Bangalore"),
    ("Delhivery", "delhivery.com", "Gurugram"),
    ("Swiggy", "swiggy.com", "Bangalore"),
    ("CRED", "cred.club", "Bangalore"),
    ("Groww", "groww.in", "Bangalore"),
    ("Zepto", "zeptonow.com", "Mumbai"),
    ("Ola Electric", "olaelectric.com", "Bangalore"),
    ("MPL (Mobile Premier League)", "mpl.live", "Bangalore"),
    ("Games24x7", "games24x7.com", "Mumbai/Bangalore"),
    ("Dream11", "dream11.com", "Mumbai"),
]

def load_naukri_seed() -> list:
    rows = []
    for name, website, city in NAUKRI_SEED:
        rows.append(row(
            Company=name,
            Website=f"https://www.{website}" if not website.startswith("http") else website,
            Source="Naukri Seed (Curated)",
            Country="India",
            City=city,
            Sector="Tech / Data / AI",
            Employer_Category="india tech",
            Hiring_Geography="India",
            Hiring_Confidence="Medium",
            Reason_Match="Top Naukri employer for Data/AI Engineering roles in India",
            Language_Requirement="English",
        ))
    return rows


# ── Main ────────────────────────────────────────────────────────────────────

def run() -> int:
    print("Scraping Naukri.com (India Data/AI jobs)...")
    all_rows = []
    seen_companies = set()

    # 1. Try API (most valuable — live, structured)
    print("  Trying Naukri API...")
    api_rows = scrape_naukri_api()
    if api_rows:
        print(f"  Naukri API: {len(api_rows)} companies")
        all_rows.extend(api_rows)
        seen_companies.update(r["Company"] for r in api_rows)
    else:
        print("  Naukri API blocked — falling through to sitemap + seed")

    # 2. Try sitemap (medium value — company names only, no roles)
    print("  Trying Naukri sitemap...")
    sitemap_rows = scrape_naukri_sitemap()
    new_sitemap = [r for r in sitemap_rows if r["Company"] not in seen_companies]
    if new_sitemap:
        print(f"  Naukri sitemap: {len(new_sitemap)} new companies")
        all_rows.extend(new_sitemap)
        seen_companies.update(r["Company"] for r in new_sitemap)
    else:
        print("  Naukri sitemap: 0 results or blocked")

    # 3. Always load seed (guaranteed coverage for top employers)
    seed_rows = load_naukri_seed()
    new_seed = [r for r in seed_rows if r["Company"] not in seen_companies]
    print(f"  Naukri seed: {len(new_seed)} companies (curated, always runs)")
    all_rows.extend(new_seed)

    if not all_rows:
        print("  Naukri: no rows produced")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    added = write_batch(all_rows, f"pipeline_naukri_{ts}")
    log_run("Naukri.com", len(all_rows))
    print(f"  Naukri total: {len(all_rows)} companies written")
    return added


if __name__ == "__main__":
    run()
