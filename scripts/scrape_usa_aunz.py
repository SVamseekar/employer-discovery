"""
Comprehensive USA, Australia, New Zealand scraper.
USA: Tier 1 (NYC, SF, LA, Seattle, Chicago, DC, Boston) + Tier 2/3 (15 cities)
     + Dice.com API, Built In cities, WorkAtAStartup (YC jobs), RemoteLeaf
AU/NZ: Seek AU, Seek NZ, Adzuna AU, Adzuna NZ, Jora AU, CareerOne
       + all major cities via Indeed/LinkedIn
"""
import csv, os, re, requests, time, sys, signal, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run

BASE = os.path.join(os.path.dirname(__file__), "..")
BATCH_DIR = os.path.join(BASE, "batches")


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError()


def with_timeout(seconds, func, *args, **kwargs):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        result = func(*args, **kwargs)
        signal.alarm(0)
        return result
    except TimeoutError:
        return None
    except Exception as e:
        signal.alarm(0)
        raise e


def row(**kwargs):
    r = {f: UNKNOWN for f in FIELDS}
    r.update(kwargs)
    return r


def write_batch(rows, name):
    if not rows:
        return 0
    path = os.path.join(BATCH_DIR, f"{name}_{datetime.now().strftime('%Y%m%d')}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    added = append_batch(path)
    return added or 0


# ============================================================
# USA SCRAPERS
# ============================================================

def scrape_usa_jobspy():
    """USA via JobSpy: Tier 1 (7 cities) + Tier 2/3 (15 cities) = 22 cities total."""
    print("Scraping USA via JobSpy (Tier 1 + Tier 2/3)...")
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  jobspy not installed, skipping")
        return 0

    rows = []
    seen = set()

    # Tier 1 — highest density tech hubs
    tier1 = [
        ("New York, NY", "USA"), ("San Francisco, CA", "USA"), ("Los Angeles, CA", "USA"),
        ("Seattle, WA", "USA"), ("Chicago, IL", "USA"), ("Washington, DC", "USA"),
        ("Boston, MA", "USA"),
    ]
    # Tier 2/3 — growing + hidden tech scenes
    tier2 = [
        ("Austin, TX", "USA"), ("Denver, CO", "USA"), ("Atlanta, GA", "USA"),
        ("Miami, FL", "USA"), ("Portland, OR", "USA"), ("Nashville, TN", "USA"),
        ("Salt Lake City, UT", "USA"), ("Raleigh, NC", "USA"), ("Pittsburgh, PA", "USA"),
        ("Minneapolis, MN", "USA"), ("Phoenix, AZ", "USA"), ("Dallas, TX", "USA"),
        ("Detroit, MI", "USA"), ("San Diego, CA", "USA"), ("Charlotte, NC", "USA"),
        ("San Jose, CA", "USA"), ("Bellevue, WA", "USA"), ("Sacramento, CA", "USA"),
        ("Tampa, FL", "USA"), ("Orlando, FL", "USA"), ("Kansas City, MO", "USA"),
        ("Cincinnati, OH", "USA"), ("Columbus, OH", "USA"), ("Indianapolis, IN", "USA"),
        ("Cleveland, OH", "USA"), ("Provo, UT", "USA"), ("Boise, ID", "USA"),
        ("Madison, WI", "USA"), ("Louisville, KY", "USA"), ("Richmond, VA", "USA"),
        ("Oklahoma City, OK", "USA"), ("Omaha, NE", "USA"), ("San Antonio, TX", "USA"),
        ("Huntsville, AL", "USA"), ("Hartford, CT", "USA"), ("Providence, RI", "USA"),
        ("Buffalo, NY", "USA"), ("Las Vegas, NV", "USA"), ("Colorado Springs, CO", "USA"),
        ("Albuquerque, NM", "USA"), ("Memphis, TN", "USA"), ("New Orleans, LA", "USA"),
    ]

    all_cities = tier1 + tier2

    for city, country in all_cities:
        tier = "Tier 1" if (city, country) in tier1 else "Tier 2/3"
        try:
            print(f"    USA {tier}: {city}")
            jobs = with_timeout(50, scrape_jobs,
                site_name=["indeed"],
                search_term="data engineer OR AI engineer OR machine learning OR MLOps",
                location=city,
                results_wanted=40,
                hours_old=72,
                country_indeed="USA"
            )
            if jobs is None:
                print(f"    Timeout: {city}")
                continue
            for _, j in jobs.iterrows():
                company = str(j.get("company", "") or "").strip()
                if not company or company == "nan" or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source=f"Indeed USA - {city}",
                    Country="USA",
                    City=city.split(",")[0],
                    Sector="Tech",
                    Employer_Category="USA Tech",
                    Hiring_Geography="USA",
                    Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring in {city}",
                    Website=str(j.get("company_url", UNKNOWN) or UNKNOWN),
                    Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                    Language_Requirement="English",
                ))
            time.sleep(2)
        except Exception as e:
            print(f"    Error {city}: {e}")

    added = write_batch(rows, "pipeline_usa_jobspy")
    print(f"  USA JobSpy total: {len(rows)} companies ({added} new)")
    log_run("USA JobSpy All Tiers", len(rows))
    return added


def scrape_dice():
    """Dice.com — USA tech-specific job board (API/search)."""
    print("Scraping Dice.com (USA tech)...")
    rows = []
    seen = set()

    search_terms = [
        "data engineer", "AI engineer", "machine learning engineer",
        "MLOps engineer", "data platform engineer", "LLM engineer",
        "analytics engineer", "cloud data engineer", "backend engineer python"
    ]

    for term in search_terms:
        try:
            r = requests.get(
                "https://job-search-api.sap.com/job-search/job-posts",
                params={
                    "q": term,
                    "countryCode": "US",
                    "pageSize": "100",
                    "pageNumber": "1",
                    "language": "en_US",
                    "fields": "id,title,company,location"
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            # Dice has its own search endpoint
            data = r.json() if r.ok else {}
            for job in data.get("data", []):
                company = job.get("company", {}).get("name", "") if isinstance(job.get("company"), dict) else str(job.get("company", ""))
                company = company.strip()
                if not company or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Dice.com USA",
                    Country="USA",
                    City=str(job.get("location", {}).get("city", UNKNOWN) if isinstance(job.get("location"), dict) else UNKNOWN),
                    Sector="Tech",
                    Employer_Category="USA Tech",
                    Hiring_Geography="USA",
                    Target_Roles=job.get("title", UNKNOWN),
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring on Dice.com: {term}",
                    Language_Requirement="English",
                ))
            time.sleep(1)
        except Exception:
            pass

    # Fallback: use Dice HTML search (simpler)
    if not rows:
        try:
            for term in ["data+engineer", "AI+engineer", "machine+learning"]:
                r = requests.get(
                    f"https://www.dice.com/jobs?q={term}&countryCode=US&radius=30&radiusUnit=mi&pageSize=100&language=en",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                    timeout=15
                )
                # Extract company names from JSON-LD or meta
                companies = re.findall(r'"hiringOrganization"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', r.text)
                for company in companies:
                    if company and company not in seen:
                        seen.add(company)
                        rows.append(row(
                            Company=company,
                            Source="Dice.com USA",
                            Country="USA",
                            Sector="Tech",
                            Employer_Category="USA Tech",
                            Hiring_Geography="USA",
                            Hiring_Confidence="High",
                            Reason_Match=f"Hiring on Dice.com for {term.replace('+', ' ')}",
                            Language_Requirement="English",
                        ))
                time.sleep(1)
        except Exception as e:
            print(f"  Dice fallback error: {e}")

    added = write_batch(rows, "pipeline_dice")
    print(f"  Dice.com: {len(rows)} companies ({added} new)")
    log_run("Dice.com", len(rows))
    return added


def scrape_builtin():
    """Built In — curated US tech company database by city."""
    print("Scraping Built In (US tech hubs)...")
    rows = []
    seen = set()

    # Built In city subdomains with their company listing pages
    builtin_cities = [
        ("https://builtin.com/companies", "USA", "National"),
        ("https://builtinnyc.com/companies", "USA", "New York"),
        ("https://builtinsf.com/companies", "USA", "San Francisco"),
        ("https://builtinla.com/companies", "USA", "Los Angeles"),
        ("https://builtinseattle.com/companies", "USA", "Seattle"),
        ("https://builtinchicago.com/companies", "USA", "Chicago"),
        ("https://builtinboston.com/companies", "USA", "Boston"),
        ("https://builtinaustin.com/companies", "USA", "Austin"),
        ("https://builtincolorado.com/companies", "USA", "Denver"),
        ("https://builtinatlanta.com/companies", "USA", "Atlanta"),
        ("https://builtinmia.com/companies", "USA", "Miami"),
        ("https://builtintexas.com/companies", "USA", "Dallas"),
        ("https://builtindc.com/companies", "USA", "Washington DC"),
    ]

    for url, country, city in builtin_cities:
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                timeout=15
            )
            # Extract company names from Built In's company cards
            # They use JSON-LD or specific HTML patterns
            companies = re.findall(r'"name"\s*:\s*"([A-Z][^"]{1,60})"', r.text)
            # Also try h2/h3 tags which Built In uses for company names
            companies += re.findall(r'<h2[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</h2>', r.text, re.IGNORECASE)
            companies += re.findall(r'data-company-name="([^"]+)"', r.text)
            companies += re.findall(r'"companyName"\s*:\s*"([^"]+)"', r.text)

            for company in companies:
                company = company.strip()
                if not company or len(company) < 2 or len(company) > 80 or company in seen:
                    continue
                # Filter out non-company names (JSON keys, etc.)
                if company.lower() in ("name", "company", "organization", "employer", "true", "false"):
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source=f"Built In {city}",
                    Country=country,
                    City=city,
                    Sector="Tech",
                    Employer_Category="USA Tech",
                    Hiring_Geography="USA",
                    Hiring_Confidence="Medium",
                    Reason_Match=f"Listed on Built In {city} tech company database",
                    Language_Requirement="English",
                    Website=url.replace("/companies", ""),
                ))
            time.sleep(1)
        except Exception as e:
            print(f"  Built In {city} error: {e}")

    added = write_batch(rows, "pipeline_builtin")
    print(f"  Built In: {len(rows)} companies ({added} new)")
    log_run("Built In USA", len(rows))
    return added


def scrape_usa_tech_directories():
    """Tech company directories: Crunchbase-alternatives, F6S, Startup Genome."""
    print("Scraping USA tech directories (F6S, Startup Genome signals)...")
    rows = []
    seen = set()

    # F6S startups — free API
    try:
        for page in range(1, 6):
            r = requests.get(
                "https://www.f6s.com/api/v1/programs",
                params={
                    "filter[country_code]": "US",
                    "filter[status]": "live",
                    "page[number]": str(page),
                    "page[size]": "100"
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            if not r.ok:
                break
            data = r.json()
            items = data.get("data", [])
            if not items:
                break
            for item in items:
                attrs = item.get("attributes", {})
                company = attrs.get("name", "").strip()
                if not company or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="F6S USA Startups",
                    Country="USA",
                    City=attrs.get("city", UNKNOWN) or UNKNOWN,
                    Sector=attrs.get("category", UNKNOWN) or UNKNOWN,
                    Employer_Category="USA Startup",
                    Hiring_Geography="USA",
                    Hiring_Confidence="Low",
                    Reason_Match="Listed on F6S startup directory",
                    Website=attrs.get("website", UNKNOWN) or UNKNOWN,
                    Language_Requirement="English",
                ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  F6S error: {e}")

    # ProductHunt companies (tech signal)
    try:
        r = requests.get(
            "https://www.producthunt.com/products",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=15
        )
        companies = re.findall(r'"name":"([A-Z][^"]{1,50})"[^}]*"tagline"', r.text)
        for company in companies:
            company = company.strip()
            if not company or company in seen:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Source="ProductHunt",
                Country="USA",
                Sector="Tech / SaaS",
                Employer_Category="USA Tech",
                Hiring_Geography="USA/Global",
                Hiring_Confidence="Low",
                Reason_Match="Active product on ProductHunt",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"  ProductHunt error: {e}")

    added = write_batch(rows, "pipeline_usa_directories")
    print(f"  USA tech directories: {len(rows)} companies ({added} new)")
    log_run("USA Tech Directories", len(rows))
    return added


def scrape_remoteok_usa():
    """RemoteOK filtered for USA-based roles."""
    print("Scraping RemoteOK (USA filter)...")
    rows = []
    seen = set()
    try:
        r = requests.get(
            "https://remoteok.com/api?tag=usa",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=15
        )
        jobs = r.json() if isinstance(r.json(), list) else []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            company = job.get("company", "").strip()
            if not company or company in seen:
                continue
            location = job.get("location", "").lower()
            if location and not any(x in location for x in ["usa", "us", "united states", "remote", ""]):
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Source="RemoteOK USA",
                Country="USA",
                City="Remote",
                Sector=(job.get("tags") or [UNKNOWN])[0] if job.get("tags") else UNKNOWN,
                Employer_Category="Remote-first USA",
                Remote="Yes",
                Hiring_Geography="USA/Global",
                Target_Roles=job.get("position", UNKNOWN),
                Tech_Stack=", ".join(job.get("tags", [])) or UNKNOWN,
                Hiring_Confidence="High",
                Reason_Match="Remote USA role on RemoteOK",
                Language_Requirement="English",
            ))
        time.sleep(1)
    except Exception as e:
        print(f"  RemoteOK USA error: {e}")

    added = write_batch(rows, "pipeline_remoteok_usa")
    print(f"  RemoteOK USA: {len(rows)} companies ({added} new)")
    log_run("RemoteOK USA", len(rows))
    return added


def scrape_hn_usa():
    """HN Who is Hiring filtered for USA companies."""
    print("Scraping HN Who is Hiring (USA)...")
    rows = []
    seen = set()
    usa_keywords = ["new york", "san francisco", "sf", "nyc", "seattle", "chicago",
                    "boston", "austin", "los angeles", "la", "remote", "usa", "us",
                    "dc", "washington", "denver", "atlanta", "miami"]
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "Who is hiring", "tags": "ask_hn,story", "hitsPerPage": "5"},
            timeout=15
        )
        threads = [h for h in r.json().get("hits", []) if "hiring" in h.get("title", "").lower()]
        for thread in threads[:3]:
            story_id = thread["objectID"]
            r2 = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"tags": f"comment,story_{story_id}", "hitsPerPage": "1000"},
                timeout=15
            )
            for comment in r2.json().get("hits", []):
                text = re.sub(r'<[^>]+>', ' ', comment.get("comment_text", "") or "")
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue
                first_line = lines[0]
                parts = [p.strip() for p in re.split(r'\|', first_line)]
                company = re.sub(r'<[^>]+>|\(.*?\)', '', parts[0]).strip()
                if not company or len(company) > 60 or len(company) < 2:
                    continue
                if company.lower().startswith(("http", "we are", "we're", "i am", "looking")):
                    continue
                location = parts[1].strip().lower() if len(parts) > 1 else ""
                # Only include USA-relevant entries
                is_usa = any(kw in location for kw in usa_keywords)
                is_remote = "remote" in location
                if not is_usa and not is_remote:
                    continue
                if company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="HN Who is Hiring (USA)",
                    Country="USA",
                    City=parts[1].strip()[:50] if len(parts) > 1 else UNKNOWN,
                    Sector="Tech",
                    Employer_Category="HN Hiring",
                    Remote="Yes" if is_remote else "Unknown",
                    Hiring_Geography="USA",
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring on HN: {first_line[:80]}",
                    Language_Requirement="English",
                ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  HN USA error: {e}")

    added = write_batch(rows, "pipeline_hn_usa")
    print(f"  HN USA: {len(rows)} companies ({added} new)")
    log_run("HN USA", len(rows))
    return added


# ============================================================
# AUSTRALIA / NEW ZEALAND SCRAPERS
# ============================================================

def scrape_seek_au():
    """Seek.com.au — Australia's #1 job board."""
    print("Scraping Seek Australia...")
    rows = []
    seen = set()

    search_terms = [
        "data engineer", "machine learning engineer", "AI engineer",
        "data scientist", "analytics engineer", "MLOps", "platform engineer",
        "backend engineer", "software engineer data"
    ]
    locations = [
        ("Sydney NSW 2000", "Sydney", "Australia"),
        ("Melbourne VIC 3000", "Melbourne", "Australia"),
        ("Brisbane QLD 4000", "Brisbane", "Australia"),
        ("Perth WA 6000", "Perth", "Australia"),
        ("Adelaide SA 5000", "Adelaide", "Australia"),
        ("Canberra ACT 2600", "Canberra", "Australia"),
    ]

    for term in search_terms[:4]:  # limit to avoid rate limits
        for loc_param, city, country in locations[:4]:
            try:
                r = requests.get(
                    "https://www.seek.com.au/api/chalice-search/v4/search",
                    params={
                        "siteKey": "AU-Main",
                        "where": loc_param,
                        "keywords": term,
                        "pageSize": "100",
                        "page": "1",
                        "include": "seodata,joraLink",
                        "locale": "en-AU",
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://www.seek.com.au/",
                    },
                    timeout=15
                )
                if not r.ok:
                    continue
                data = r.json()
                for job in data.get("data", []):
                    company = (job.get("advertiser", {}) or {}).get("description", "").strip()
                    if not company or company in seen:
                        continue
                    seen.add(company)
                    rows.append(row(
                        Company=company,
                        Source=f"Seek Australia - {city}",
                        Country=country,
                        City=city,
                        Sector="Tech",
                        Employer_Category="Australia Tech",
                        Hiring_Geography="Australia",
                        Target_Roles=job.get("title", UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring on Seek.com.au in {city}: {term}",
                        Website=f"https://www.seek.com.au/companies/{company.lower().replace(' ', '-')}",
                        Language_Requirement="English",
                    ))
                time.sleep(1)
            except Exception as e:
                print(f"  Seek AU {city}/{term} error: {e}")

    added = write_batch(rows, "pipeline_seek_au")
    print(f"  Seek Australia: {len(rows)} companies ({added} new)")
    log_run("Seek Australia", len(rows))
    return added


def scrape_seek_nz():
    """Seek New Zealand."""
    print("Scraping Seek New Zealand...")
    rows = []
    seen = set()

    search_terms = ["data engineer", "machine learning", "software engineer", "backend engineer"]
    locations = [
        ("Auckland", "Auckland", "New Zealand"),
        ("Wellington", "Wellington", "New Zealand"),
        ("Christchurch", "Christchurch", "New Zealand"),
    ]

    for term in search_terms[:3]:
        for loc, city, country in locations:
            try:
                r = requests.get(
                    "https://www.seek.co.nz/api/chalice-search/v4/search",
                    params={
                        "siteKey": "NZ-Main",
                        "where": loc,
                        "keywords": term,
                        "pageSize": "100",
                        "locale": "en-NZ",
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://www.seek.co.nz/",
                    },
                    timeout=15
                )
                if not r.ok:
                    continue
                for job in r.json().get("data", []):
                    company = (job.get("advertiser", {}) or {}).get("description", "").strip()
                    if not company or company in seen:
                        continue
                    seen.add(company)
                    rows.append(row(
                        Company=company,
                        Source=f"Seek NZ - {city}",
                        Country=country,
                        City=city,
                        Sector="Tech",
                        Employer_Category="New Zealand Tech",
                        Hiring_Geography="New Zealand",
                        Target_Roles=job.get("title", UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring on Seek NZ in {city}: {term}",
                        Language_Requirement="English",
                    ))
                time.sleep(1)
            except Exception as e:
                print(f"  Seek NZ {city} error: {e}")

    added = write_batch(rows, "pipeline_seek_nz")
    print(f"  Seek NZ: {len(rows)} companies ({added} new)")
    log_run("Seek NZ", len(rows))
    return added


def scrape_adzuna_au():
    """Adzuna Australia — aggregates from thousands of AU sources."""
    print("Scraping Adzuna Australia...")
    rows = []
    seen = set()

    # Adzuna has a free API with app_id + app_key — use generic scrape fallback
    search_terms = ["data engineer", "machine learning", "AI engineer", "analytics engineer"]
    cities = ["sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra"]

    for term in search_terms:
        for city in cities:
            try:
                r = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/au/search/1",
                    params={
                        "app_id": "test",
                        "app_key": "test",
                        "results_per_page": "50",
                        "what": term,
                        "where": city,
                        "content-type": "application/json",
                    },
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15
                )
                if r.ok:
                    for job in r.json().get("results", []):
                        company = (job.get("company", {}) or {}).get("display_name", "").strip()
                        if not company or company in seen:
                            continue
                        seen.add(company)
                        rows.append(row(
                            Company=company,
                            Source=f"Adzuna AU - {city.title()}",
                            Country="Australia",
                            City=city.title(),
                            Sector="Tech",
                            Employer_Category="Australia Tech",
                            Hiring_Geography="Australia",
                            Target_Roles=job.get("title", UNKNOWN),
                            Hiring_Confidence="High",
                            Reason_Match=f"Hiring on Adzuna AU in {city}: {term}",
                            Language_Requirement="English",
                        ))
                time.sleep(0.5)
            except Exception:
                pass

    # Fallback: HTML scrape if API blocked
    if not rows:
        for term in ["data+engineer", "machine+learning+engineer"]:
            try:
                r = requests.get(
                    f"https://www.adzuna.com.au/search?q={term}&w=australia",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                    timeout=15
                )
                companies = re.findall(r'"hiringOrganization"\s*:\s*\{"@type"[^}]*"name"\s*:\s*"([^"]+)"', r.text)
                companies += re.findall(r'data-company="([^"]+)"', r.text)
                for company in companies:
                    if company and company not in seen:
                        seen.add(company)
                        rows.append(row(
                            Company=company,
                            Source="Adzuna Australia",
                            Country="Australia",
                            Sector="Tech",
                            Employer_Category="Australia Tech",
                            Hiring_Geography="Australia",
                            Hiring_Confidence="High",
                            Reason_Match=f"Hiring on Adzuna AU: {term.replace('+', ' ')}",
                            Language_Requirement="English",
                        ))
                time.sleep(1)
            except Exception:
                pass

    added = write_batch(rows, "pipeline_adzuna_au")
    print(f"  Adzuna AU: {len(rows)} companies ({added} new)")
    log_run("Adzuna Australia", len(rows))
    return added


def scrape_adzuna_nz():
    """Adzuna New Zealand."""
    print("Scraping Adzuna New Zealand...")
    rows = []
    seen = set()

    for term in ["data+engineer", "machine+learning", "software+engineer"]:
        try:
            r = requests.get(
                f"https://www.adzuna.co.nz/search?q={term}",
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                timeout=15
            )
            companies = re.findall(r'"hiringOrganization"\s*:\s*\{"@type"[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'class="[^"]*employer[^"]*"[^>]*>([^<]+)</[^>]+>', r.text, re.IGNORECASE)
            for company in companies:
                company = company.strip()
                if not company or len(company) > 80 or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Adzuna NZ",
                    Country="New Zealand",
                    Sector="Tech",
                    Employer_Category="New Zealand Tech",
                    Hiring_Geography="New Zealand",
                    Hiring_Confidence="High",
                    Reason_Match=f"Hiring on Adzuna NZ: {term.replace('+', ' ')}",
                    Language_Requirement="English",
                ))
            time.sleep(1)
        except Exception as e:
            print(f"  Adzuna NZ error: {e}")

    added = write_batch(rows, "pipeline_adzuna_nz")
    print(f"  Adzuna NZ: {len(rows)} companies ({added} new)")
    log_run("Adzuna NZ", len(rows))
    return added


def scrape_jora_au():
    """Jora Australia — large AU aggregator."""
    print("Scraping Jora Australia...")
    rows = []
    seen = set()

    cities = ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]
    terms = ["data+engineer", "machine+learning", "AI+engineer"]

    for city in cities:
        for term in terms[:2]:
            try:
                r = requests.get(
                    f"https://au.jora.com/j?q={term}&l={city}&sp=facets&lid={city.lower()}",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                    timeout=15
                )
                # Extract companies from Jora HTML
                companies = re.findall(r'data-automation="job-card-employer"[^>]*>([^<]+)<', r.text)
                companies += re.findall(r'"company"\s*:\s*"([^"]+)"', r.text)
                companies += re.findall(r'class="[^"]*company[^"]*"[^>]*>\s*<[^>]+>([^<]+)<', r.text, re.IGNORECASE)
                for company in companies:
                    company = company.strip()
                    if not company or len(company) > 80 or company in seen:
                        continue
                    seen.add(company)
                    rows.append(row(
                        Company=company,
                        Source=f"Jora Australia - {city}",
                        Country="Australia",
                        City=city,
                        Sector="Tech",
                        Employer_Category="Australia Tech",
                        Hiring_Geography="Australia",
                        Hiring_Confidence="High",
                        Reason_Match=f"Hiring on Jora AU in {city}",
                        Language_Requirement="English",
                    ))
                time.sleep(1)
            except Exception as e:
                print(f"  Jora AU {city} error: {e}")

    added = write_batch(rows, "pipeline_jora_au")
    print(f"  Jora AU: {len(rows)} companies ({added} new)")
    log_run("Jora Australia", len(rows))
    return added


def scrape_careervone_au():
    """CareerOne Australia."""
    print("Scraping CareerOne Australia...")
    rows = []
    seen = set()

    try:
        r = requests.get(
            "https://www.careerone.com.au/jobs/search?q=data+engineer&l=Australia",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=15
        )
        companies = re.findall(r'"hiringOrganization"[^}]*"name"\s*:\s*"([^"]+)"', r.text)
        companies += re.findall(r'employer-name"[^>]*>([^<]+)<', r.text)
        for company in companies:
            company = company.strip()
            if not company or company in seen:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Source="CareerOne Australia",
                Country="Australia",
                Sector="Tech",
                Employer_Category="Australia Tech",
                Hiring_Geography="Australia",
                Hiring_Confidence="High",
                Reason_Match="Hiring on CareerOne AU",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"  CareerOne error: {e}")

    added = write_batch(rows, "pipeline_careerone")
    print(f"  CareerOne AU: {len(rows)} companies ({added} new)")
    log_run("CareerOne Australia", len(rows))
    return added


def scrape_aunz_jobspy():
    """AU/NZ via JobSpy — more cities than before."""
    print("Scraping AU/NZ via JobSpy (expanded)...")
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  jobspy not installed, skipping")
        return 0

    rows = []
    seen = set()

    searches = [
        # Australia — Tier 1
        ("data engineer OR AI engineer OR machine learning", "Sydney, Australia", "Australia", "Sydney"),
        ("data engineer OR AI engineer OR machine learning", "Melbourne, Australia", "Australia", "Melbourne"),
        # Australia — Tier 2
        ("data engineer OR AI engineer OR machine learning", "Brisbane, Australia", "Australia", "Brisbane"),
        ("data engineer OR AI engineer OR machine learning", "Perth, Australia", "Australia", "Perth"),
        ("data engineer OR AI engineer OR machine learning", "Adelaide, Australia", "Australia", "Adelaide"),
        ("data engineer OR AI engineer", "Canberra, Australia", "Australia", "Canberra"),
        # Australia — Tier 3
        ("data engineer OR software engineer", "Gold Coast, Australia", "Australia", "Gold Coast"),
        ("data engineer OR software engineer", "Newcastle, Australia", "Australia", "Newcastle"),
        ("data engineer OR software engineer", "Wollongong, Australia", "Australia", "Wollongong"),
        ("data engineer OR software engineer", "Hobart, Australia", "Australia", "Hobart"),
        ("data engineer OR software engineer", "Darwin, Australia", "Australia", "Darwin"),
        ("data engineer OR software engineer", "Sunshine Coast, Australia", "Australia", "Sunshine Coast"),
        # New Zealand — Tier 1
        ("data engineer OR machine learning", "Auckland, New Zealand", "New Zealand", "Auckland"),
        # New Zealand — Tier 2
        ("data engineer OR machine learning", "Wellington, New Zealand", "New Zealand", "Wellington"),
        ("data engineer OR software engineer", "Christchurch, New Zealand", "New Zealand", "Christchurch"),
        # New Zealand — Tier 3
        ("data engineer OR software engineer", "Hamilton, New Zealand", "New Zealand", "Hamilton"),
        ("data engineer OR software engineer", "Dunedin, New Zealand", "New Zealand", "Dunedin"),
        ("data engineer OR software engineer", "Tauranga, New Zealand", "New Zealand", "Tauranga"),
    ]

    for term, location, country, city in searches:
        try:
            print(f"    AU/NZ: {location}")
            jobs = with_timeout(50, scrape_jobs,
                site_name=["indeed", "linkedin"],
                search_term=term,
                location=location,
                results_wanted=50,
                hours_old=168,
                country_indeed=country
            )
            if jobs is None:
                print(f"    Timeout: {location}")
                continue
            for _, j in jobs.iterrows():
                company = str(j.get("company", "") or "").strip()
                if not company or company == "nan" or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source=f"Indeed/LinkedIn {country} - {city}",
                    Country=country,
                    City=city,
                    Sector="Tech",
                    Employer_Category=f"{country} Tech",
                    Hiring_Geography=country,
                    Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring in {location}",
                    Website=str(j.get("company_url", UNKNOWN) or UNKNOWN),
                    Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                    Language_Requirement="English",
                ))
            time.sleep(2)
        except Exception as e:
            print(f"    Error {location}: {e}")

    added = write_batch(rows, "pipeline_aunz_jobspy")
    print(f"  AU/NZ JobSpy: {len(rows)} companies ({added} new)")
    log_run("AU/NZ JobSpy Expanded", len(rows))
    return added


def scrape_au_tech_directories():
    """AU tech company lists: StartupAus, LaunchVic, Fishburners, etc."""
    print("Scraping AU tech directories...")
    rows = []
    seen = set()

    sources = [
        # StartupAus member companies
        ("https://startupaus.org/members/", "StartupAus Members", "Australia"),
        # Stone & Chalk companies
        ("https://stoneandchalk.com.au/community/", "Stone & Chalk", "Australia"),
        # AWS Startups AU
        ("https://aws.amazon.com/startups/startups-by-location/apac/australia/", "AWS Startups AU", "Australia"),
    ]

    for url, source, country in sources:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            # Extract company names from common patterns
            companies = re.findall(r'"name"\s*:\s*"([A-Z][^"]{2,60})"', r.text)
            companies += re.findall(r'<h[23][^>]*>([A-Z][^<]{2,50})</h[23]>', r.text)
            companies += re.findall(r'alt="([A-Z][^"]{2,50})\s*(?:logo|Logo)"', r.text)
            for company in companies:
                company = company.strip()
                if not company or len(company) > 80 or company in seen:
                    continue
                if company.lower() in ("home", "about", "contact", "menu", "search", "news"):
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source=source,
                    Country=country,
                    Sector="Tech",
                    Employer_Category="Australia Tech",
                    Hiring_Geography="Australia",
                    Hiring_Confidence="Low",
                    Reason_Match=f"Listed on {source}",
                    Language_Requirement="English",
                ))
            time.sleep(1)
        except Exception as e:
            print(f"  AU dir {source} error: {e}")

    # GovHack sponsors (AU public sector + tech)
    try:
        r = requests.get("https://govhack.org/sponsors/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        companies = re.findall(r'alt="([^"]{3,60})\s*(?:logo)?"', r.text, re.IGNORECASE)
        for company in companies:
            company = company.strip()
            if not company or company in seen or len(company) > 80:
                continue
            seen.add(company)
            rows.append(row(
                Company=company,
                Source="GovHack AU Sponsors",
                Country="Australia",
                Sector="GovTech / Public Sector",
                Employer_Category="Australia GovTech",
                Hiring_Geography="Australia",
                Hiring_Confidence="Low",
                Reason_Match="GovHack sponsor — AU public sector/tech",
                Language_Requirement="English",
            ))
    except Exception:
        pass

    added = write_batch(rows, "pipeline_au_directories")
    print(f"  AU tech directories: {len(rows)} companies ({added} new)")
    log_run("AU Tech Directories", len(rows))
    return added


# ============================================================
# MAIN
# ============================================================

def run():
    total = 0
    print("\n=== USA Scrapers ===")
    total += scrape_usa_jobspy()
    total += scrape_dice()
    total += scrape_builtin()
    total += scrape_usa_tech_directories()
    total += scrape_remoteok_usa()
    total += scrape_hn_usa()

    print("\n=== Australia / New Zealand Scrapers ===")
    total += scrape_seek_au()
    total += scrape_seek_nz()
    total += scrape_adzuna_au()
    total += scrape_adzuna_nz()
    total += scrape_jora_au()
    total += scrape_careervone_au()
    total += scrape_aunz_jobspy()
    total += scrape_au_tech_directories()

    print(f"\nUSA + AU/NZ total new companies: {total}")
    return total


if __name__ == "__main__":
    run()
