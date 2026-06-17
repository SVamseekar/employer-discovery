"""
Run all pipeline scrapers directly — no n8n needed for CSV writes.
Results go straight to data/master_employers.csv.
Usage: python scripts/run_scrapers.py

ARCHITECTURE (layers, most reliable → least reliable):
  Layer 0: static_companies.py  — 300+ hardcoded FAANG/MNCs (never blocked)
  Layer 1: API sources           — YC, RemoteOK, GitHub, Remotive (API, reliable)
  Layer 2: VC portfolios         — EU/US/India/AU VC portfolio HTML (reliable)
  Layer 3: JobSpy/Indeed         — city-by-city job board scraping (fragile)
  Layer 4: Direct portal scrapers — Dice, Built In, Naukri etc. (often blocked)

Failures in layers 3-4 are logged to data/scraper_errors.log and skipped.
The pipeline never crashes from a single blocked source.
"""
import csv, os, requests, json, sys, time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run
from static_companies import load_static_companies
from scraper_utils import github_headers

ERROR_LOG = os.path.join(os.path.dirname(__file__), "..", "data", "scraper_errors.log")

def log_scraper_error(source, detail, error):
    """Append a scraper failure to the error log without crashing the pipeline."""
    try:
        os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            f.write(f"[{ts}] SOURCE={source} | DETAIL={detail} | ERROR={str(error)[:200]}\n")
    except Exception:
        pass  # never crash the pipeline over log writes

MASTER = os.path.join(os.path.dirname(__file__), "..", "data", "master_employers.csv")
BATCH_DIR = os.path.join(os.path.dirname(__file__), "..", "batches")

def write_batch(rows, name):
    path = os.path.join(BATCH_DIR, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    append_batch(path)
    return path

def row(**kwargs):
    r = {f: UNKNOWN for f in FIELDS}
    r.update(kwargs)
    return r

# --- Layer 0: Static curated company list ---
def load_static():
    """
    Load 300+ hardcoded FAANG/MNCs/regional top employers.
    This layer NEVER fails — no network calls, no bot detection, no timeouts.
    Run first so the master CSV always has a solid foundation.
    """
    print("Loading static company list (Layer 0)...")
    try:
        companies = load_static_companies()
        # Convert to full schema rows (static_companies.py already returns schema-compatible dicts)
        rows = []
        for co in companies:
            r = {f: UNKNOWN for f in FIELDS}
            r.update(co)
            rows.append(r)
        write_batch(rows, f"pipeline_static_{datetime.now().strftime('%Y%m%d')}")
        print(f"  Static list: {len(rows)} companies loaded (FAANG + MNCs + regional leaders)")
        log_run("Static Company List", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  Static list error (this should never happen): {e}")
        log_scraper_error("static_companies", "load_static_companies()", e)
        return 0


# --- Scraper 1: YC Directory ---
def scrape_yc():
    print("Scraping YC Directory...")
    try:
        all_companies = []
        for page in range(1, 5):  # fetch 4 pages of 100
            r = requests.get(
                "https://api.ycombinator.com/v0.1/companies",
                params={"limit": "100", "page": str(page)},
                timeout=15
            )
            batch = r.json().get("companies", [])
            if not batch:
                break
            all_companies.extend(batch)
            time.sleep(0.5)
        companies = all_companies
        rows = []
        for c in companies:
            rows.append(row(
                Company=c.get("name", UNKNOWN),
                Website=c.get("website", UNKNOWN),
                Careers_URL=(c.get("website", "") + "/careers") if c.get("website") else UNKNOWN,
                Country=c.get("country", "USA"),
                City=c.get("city", UNKNOWN),
                Sector=" / ".join(c.get("tags", [])) or UNKNOWN,
                Company_Stage="Startup",
                Employer_Category="YC",
                Hiring_Confidence="Low",
                Reason_Match="YC company — " + (c.get("one_liner") or ""),
                Source="YC Directory API",
                Language_Requirement="None",
            ))
        write_batch(rows, f"pipeline_yc_{datetime.now().strftime('%Y%m%d')}")
        print(f"  YC: {len(rows)} companies")
        log_run("YC Directory API", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  YC error: {e}")
        return 0

# --- Scraper 2: RemoteOK ---
def scrape_remoteok():
    print("Scraping RemoteOK...")
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=15
        )
        jobs = r.json()
        seen = set()
        rows = []
        for job in (jobs if isinstance(jobs, list) else []):
            company = job.get("company", "")
            if not company or company in seen:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Website=job.get("url", UNKNOWN),
                Careers_URL=job.get("apply_url", UNKNOWN),
                City="Remote",
                Sector=(job.get("tags") or [UNKNOWN])[0],
                Employer_Category="Remote-first",
                Remote="Yes",
                Hiring_Geography="Global",
                Target_Roles=job.get("position", UNKNOWN),
                Tech_Stack=", ".join(job.get("tags", [])) or UNKNOWN,
                Region_Eligibility="Global",
                Hiring_Confidence="Medium",
                Reason_Match="Actively hiring remotely on RemoteOK",
                Source="RemoteOK API",
                Language_Requirement="None",
            ))
        write_batch(rows, f"pipeline_remoteok_{datetime.now().strftime('%Y%m%d')}")
        print(f"  RemoteOK: {len(rows)} companies")
        log_run("RemoteOK API", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  RemoteOK error: {e}")
        return 0

# --- Scraper 3: GitHub Stack Signal ---
def scrape_github():
    print("Scraping GitHub Stack Signal...")
    queries = [
        "rag retrieval augmented generation language:python stars:>10",
        "dbt data build tool analytics language:sql stars:>10",
        "llm inference fastapi python stars:>10",
        "databricks spark data engineering stars:>10",
    ]
    seen = set()
    rows = []
    for q in queries:
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "updated", "per_page": "30"},
                headers=github_headers(),
                timeout=20
            )
            if r.status_code == 403:
                print("  GitHub rate limited — set GITHUB_TOKEN env for 5k req/hr")
                break
            repos = r.json().get("items", [])
            for repo in repos:
                owner = repo.get("owner", {})
                if owner.get("type") != "Organization":
                    continue
                org = owner.get("login", "")
                if not org or org in seen:
                    continue
                seen.add(org)
                rows.append(row(
                    Company=org,
                    Website=f"https://github.com/{org}",
                    Sector="AI Infrastructure",
                    Employer_Category="GitHub Signal",
                    Target_Roles="AI Engineer / Data Engineer",
                    Tech_Stack=", ".join(repo.get("topics", [])) or repo.get("language", UNKNOWN),
                    Hiring_Confidence="Low",
                    Reason_Match=f"GitHub org with active repos matching stack: {repo.get('full_name','')}",
                    Source="GitHub API Stack Signal",
                    Language_Requirement="None",
                ))
            time.sleep(1)  # respect rate limit
        except Exception as e:
            print(f"  GitHub query error: {e}")
    write_batch(rows, f"pipeline_github_{datetime.now().strftime('%Y%m%d')}")
    print(f"  GitHub: {len(rows)} orgs")
    log_run("GitHub API Stack Signal", len(rows))
    return len(rows)

# --- Scraper 4: Remotive ---
def scrape_remotive():
    print("Scraping Remotive...")
    try:
        r = requests.get("https://remotive.com/api/remote-jobs", params={"limit": "200"}, timeout=15)
        jobs = r.json().get("jobs", [])
        seen = set()
        rows = []
        for j in jobs:
            company = j.get("company_name", "")
            if not company or company in seen:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Website=j.get("company_url", "") or j.get("url", UNKNOWN),
                Careers_URL=j.get("url", UNKNOWN),
                Country=j.get("candidate_required_location", "Remote"),
                City="Remote",
                Sector=", ".join(j.get("tags", [])) or UNKNOWN,
                Employer_Category="Remote-First",
                Remote="Yes",
                Hiring_Geography=j.get("candidate_required_location", "Worldwide"),
                Target_Roles=j.get("title", UNKNOWN),
                Tech_Stack=", ".join(j.get("tags", [])) or UNKNOWN,
                Hiring_Confidence="High",
                Reason_Match=(j.get("title", "") or "")[:100],
                Source="Remotive API",
                Language_Requirement="English",
            ))
        write_batch(rows, f"pipeline_remotive_{datetime.now().strftime('%Y%m%d')}")
        print(f"  Remotive: {len(rows)} companies")
        log_run("Remotive API", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  Remotive error: {e}")
        return 0


# --- Scraper 5: EU Startup Directories (Euroboom + Dealroom public) ---
def scrape_eu_startups():
    print("Scraping EU Startup Directories...")
    rows = []
    seen = set()

    # Euroboom — free JSON list of EU startups
    sources = [
        ("https://raw.githubusercontent.com/nicholasgasior/euroboom/master/data/startups.json", "eu_name", "eu_url"),
    ]

    # Remotive filtered for Europe
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": "200", "search": "europe"},
            timeout=15
        )
        for j in r.json().get("jobs", []):
            loc = j.get("candidate_required_location", "")
            if not any(x in loc.lower() for x in ["europe", "eu", "germany", "netherlands", "france", "sweden", "spain", "poland"]):
                continue
            company = j.get("company_name", "")
            if not company or company in seen:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Careers_URL=j.get("url", UNKNOWN),
                Country=loc or "Europe",
                City="Remote",
                Sector=", ".join(j.get("tags", [])) or UNKNOWN,
                Employer_Category="EU Remote",
                Remote="Yes",
                Hiring_Geography=loc or "Europe",
                Target_Roles=j.get("title", UNKNOWN),
                Tech_Stack=", ".join(j.get("tags", [])) or UNKNOWN,
                Hiring_Confidence="High",
                Reason_Match=(j.get("title", "") or "")[:100],
                Source="Remotive EU",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"  Remotive EU error: {e}")

    if rows:
        write_batch(rows, f"pipeline_eu_{datetime.now().strftime('%Y%m%d')}")
    print(f"  EU Startups: {len(rows)} companies")
    log_run("EU Startup Directories", len(rows))
    return len(rows)


# --- Scraper 6: India — Tier 1 / 2 / 3 cities via JobSpy ---
def scrape_india():
    """
    India city-by-city scrape across Tier 1/2/3 — mirrors the EU/USA tiering strategy.
    Tier 1: Bangalore, Mumbai, Delhi/NCR, Hyderabad, Chennai
    Tier 2: Pune, Kolkata, Ahmedabad, Noida, Gurgaon, Coimbatore
    Tier 3: Jaipur, Kochi, Indore, Chandigarh, Bhubaneswar, Nagpur, Mysore, Lucknow
    """
    print("Scraping India jobs (Tier 1/2/3 cities via Indeed + LinkedIn)...")
    try:
        from jobspy import scrape_jobs
        import signal as _signal

        class _Timeout(Exception):
            pass

        def _handler(s, f):
            raise _Timeout()

        def _with_timeout(sec, fn, *a, **kw):
            _signal.signal(_signal.SIGALRM, _handler)
            _signal.alarm(sec)
            try:
                res = fn(*a, **kw)
                _signal.alarm(0)
                return res
            except _Timeout:
                return None
            except Exception as e:
                _signal.alarm(0)
                raise e

        india_cities = [
            # Tier 1 — largest tech ecosystems
            ("Bangalore, Karnataka", "Bangalore"),
            ("Mumbai, Maharashtra", "Mumbai"),
            ("Delhi, Delhi", "Delhi"),
            ("Hyderabad, Telangana", "Hyderabad"),
            ("Chennai, Tamil Nadu", "Chennai"),
            # Tier 2 — major secondary hubs
            ("Pune, Maharashtra", "Pune"),
            ("Kolkata, West Bengal", "Kolkata"),
            ("Ahmedabad, Gujarat", "Ahmedabad"),
            ("Noida, Uttar Pradesh", "Noida"),
            ("Gurgaon, Haryana", "Gurgaon"),
            ("Coimbatore, Tamil Nadu", "Coimbatore"),
            # Tier 3 — rising tech cities
            ("Jaipur, Rajasthan", "Jaipur"),
            ("Kochi, Kerala", "Kochi"),
            ("Indore, Madhya Pradesh", "Indore"),
            ("Chandigarh, Punjab", "Chandigarh"),
            ("Bhubaneswar, Odisha", "Bhubaneswar"),
            ("Nagpur, Maharashtra", "Nagpur"),
            ("Mysore, Karnataka", "Mysore"),
            ("Lucknow, Uttar Pradesh", "Lucknow"),
        ]

        seen = set()
        rows = []

        for location, city in india_cities:
            try:
                print(f"    India: {city}")
                jobs = _with_timeout(45, scrape_jobs,
                    site_name=["indeed", "linkedin"],
                    search_term="data engineer OR AI engineer OR machine learning OR MLOps",
                    location=location,
                    results_wanted=40,
                    hours_old=72,
                    country_indeed="India"
                )
                if jobs is None:
                    print(f"    Timeout: {city}")
                    log_scraper_error("Indeed India", city, "SIGALRM timeout after 45s")
                    continue
                for _, j in jobs.iterrows():
                    company = str(j.get("company", "") or "").strip()
                    if not company or company == "nan" or company in seen:
                        continue
                    seen.add(company)
                    rows.append(row(
                        Company=company,
                        Source=f"Indeed/LinkedIn India - {city}",
                        Country="India",
                        City=city,
                        Sector="Tech",
                        Employer_Category="India Tech",
                        Remote="Unknown",
                        Hiring_Geography="India",
                        Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring in {city}: {str(j.get('title',''))[:80]}",
                        Website=UNKNOWN,
                        Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                        Language_Requirement="English",
                    ))
                time.sleep(2)
            except Exception as e:
                print(f"    India {city} error: {e}")
                log_scraper_error("Indeed India", city, e)

        write_batch(rows, f"pipeline_india_{datetime.now().strftime('%Y%m%d')}")
        print(f"  India: {len(rows)} companies across {len(india_cities)} cities")
        log_run("India Tier 1/2/3 Cities", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  India scraper error: {e}")
        return 0


# --- Scraper 7: Japan — Tier 1 / 2 / 3 cities via JobSpy ---
def scrape_japan():
    """
    Japan city-by-city scrape. English-first roles prioritised (many global companies
    and foreign-friendly startups in Tokyo explicitly list English).
    Tier 1: Tokyo, Osaka
    Tier 2: Yokohama, Nagoya, Fukuoka, Sapporo, Kyoto
    Tier 3: Sendai, Hiroshima, Kobe, Kawasaki
    Note: Language_Requirement set to 'Japanese (Learning)' so the email
          pipeline adds the honest learning acknowledgment line.
    """
    print("Scraping Japan jobs (Tier 1/2/3 cities via Indeed)...")
    try:
        from jobspy import scrape_jobs
        import signal as _signal

        class _Timeout(Exception):
            pass

        def _handler(s, f):
            raise _Timeout()

        def _with_timeout(sec, fn, *a, **kw):
            _signal.signal(_signal.SIGALRM, _handler)
            _signal.alarm(sec)
            try:
                res = fn(*a, **kw)
                _signal.alarm(0)
                return res
            except _Timeout:
                return None
            except Exception as e:
                _signal.alarm(0)
                raise e

        japan_cities = [
            # Tier 1
            ("Tokyo", "Tokyo"),
            ("Osaka", "Osaka"),
            # Tier 2
            ("Yokohama", "Yokohama"),
            ("Nagoya", "Nagoya"),
            ("Fukuoka", "Fukuoka"),
            ("Sapporo", "Sapporo"),
            ("Kyoto", "Kyoto"),
            # Tier 3
            ("Sendai", "Sendai"),
            ("Hiroshima", "Hiroshima"),
            ("Kobe", "Kobe"),
            ("Kawasaki", "Kawasaki"),
        ]

        # Search terms targeting English-friendly / international roles
        search_terms = [
            "data engineer English",
            "AI engineer English",
            "machine learning engineer",
            "software engineer data",
        ]

        seen = set()
        rows = []

        for city, city_name in japan_cities:
            for term in search_terms[:2]:  # limit per city to control runtime
                try:
                    print(f"    Japan: {city_name}")
                    jobs = _with_timeout(45, scrape_jobs,
                        site_name=["indeed"],
                        search_term=term,
                        location=f"{city}, Japan",
                        results_wanted=25,
                        hours_old=168,  # 1 week — Japan boards update less frequently
                        country_indeed="Japan"
                    )
                    if jobs is None:
                        print(f"    Timeout: {city_name}")
                        continue
                    for _, j in jobs.iterrows():
                        company = str(j.get("company", "") or "").strip()
                        if not company or company == "nan" or company in seen:
                            continue
                        seen.add(company)
                        rows.append(row(
                            Company=company,
                            Source=f"Indeed Japan - {city_name}",
                            Country="Japan",
                            City=city_name,
                            Sector="Tech",
                            Employer_Category="Japan Tech",
                            Remote="Unknown",
                            Hiring_Geography="Japan",
                            Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                            Hiring_Confidence="Medium",
                            Reason_Match=f"Hiring in {city_name}: {str(j.get('title',''))[:80]}",
                            Website=UNKNOWN,
                            Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                            Language_Requirement="Japanese (Learning)",
                        ))
                    time.sleep(2)
                except Exception as e:
                    print(f"    Japan {city_name} error: {e}")
                    log_scraper_error("Indeed Japan", city_name, e)

        write_batch(rows, f"pipeline_japan_{datetime.now().strftime('%Y%m%d')}")
        print(f"  Japan: {len(rows)} companies across {len(japan_cities)} cities")
        log_run("Japan Tier 1/2/3 Cities", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  Japan scraper error: {e}")
        return 0


if __name__ == "__main__":
    print(f"\nPipeline run started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    total = 0

    # ── Layer 0: Static foundation — always runs first ──────────────────
    total += load_static()

    # ── Layer 1: API sources (reliable) ─────────────────────────────────
    total += scrape_yc()
    total += scrape_remoteok()
    total += scrape_github()
    total += scrape_remotive()
    # ── Layer 2: VC portfolios + EU startups (reliable HTML scraping) ────
    total += scrape_eu_startups()

    # ── Layer 3: City-by-city JobSpy/Indeed (fragile — log failures) ─────
    total += scrape_india()
    total += scrape_japan()

    # Layer 2: Directory scrapers (VC portfolios, public lists)
    from scrape_scaling_europe import run as scaling_run
    total += scaling_run()

    # Layer 3: JobSpy city-by-city (accepts partial failures — see scraper_errors.log)
    from scrape_directories import run as dir_run
    total += dir_run()

    # Layer 3: USA + AU/NZ JobSpy coverage
    from scrape_usa_aunz import run as usa_aunz_run
    total += usa_aunz_run()

    # Layer 2: EU portals (80 portals + VC portfolios including India VCs — HTML scraping)
    from scrape_eu_portals import run as eu_portals_run
    total += eu_portals_run()

    # Layer 2: Naukri.com — API → sitemap → curated seed (India Data/AI jobs)
    from scrape_naukri import run as naukri_run
    total += naukri_run()

    print(f"\n{'='*60}")
    print(f"Pipeline complete. Total employers processed this run: {total}")
    print(f"Check data/scraper_errors.log for any blocked sources.")
    print(f"{'='*60}")

    from visa_crossref import run as visa_run
    visa_run()

    from score_shortlist import run as score_run
    score_run()

    from enrich_shortlist import run as enrich_run
    enrich_run()
