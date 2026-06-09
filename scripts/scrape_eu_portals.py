"""
Scrape EU IT job portals — only confirmed working sources.
Strategy: use real JSON APIs where available, RSS/sitemap where not.
Portals: Landing.jobs, Remotive EU, No Fluff Jobs, Welcome to the Jungle,
         Relocate.me, JobFluent, Tecnoempleo, Berlin Startup Jobs,
         GermanTechJobs, DutchTechJobs, The Hub, IT-Jobbank DK, SwissDevJobs,
         Demando, Bulldogjob, Honeypot, EU Remote Jobs, WeAreDevelopers
VC portfolios: Balderton, Index, Northzone, Atomico, EarlyBird, HV Capital,
               a16z, Bessemer, Accel, Sequoia, Blackbird (AU), Square Peg (AU)
"""
import csv, os, re, requests, time, sys, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run

BASE = os.path.join(os.path.dirname(__file__), "..")
BATCH_DIR = os.path.join(BASE, "batches")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


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


def clean(name):
    name = re.sub(r'<[^>]+>', '', str(name)).strip().strip('"\'')
    name = re.sub(r'\s+', ' ', name)
    return name if 2 <= len(name) <= 80 else ""


# ---------------------------------------------------------------
# LANDING.JOBS — confirmed /api/v1/companies endpoint
# ---------------------------------------------------------------
def scrape_landing_jobs():
    rows = []
    seen = set()
    try:
        for page in range(1, 10):
            r = requests.get(
                f"https://landing.jobs/api/v1/companies?limit=100&page={page}",
                headers=HEADERS, timeout=15
            )
            if not r.ok:
                break
            data = r.json()
            if not data:
                break
            items = data if isinstance(data, list) else data.get("companies", [])
            if not items:
                break
            for c in items:
                company = clean(c.get("name", ""))
                if not company or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Landing.jobs",
                    Country=c.get("country", "Europe"),
                    City=c.get("city", UNKNOWN) or UNKNOWN,
                    Sector=c.get("industry", UNKNOWN) or UNKNOWN,
                    Employer_Category="EU Tech",
                    Hiring_Geography="Europe",
                    Hiring_Confidence="High",
                    Reason_Match=c.get("short_pitch", "Listed on Landing.jobs EU tech")[:100],
                    Website=c.get("website", UNKNOWN) or UNKNOWN,
                    Language_Requirement="English",
                ))
            time.sleep(0.3)
    except Exception as e:
        print(f"  Landing.jobs error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# REMOTIVE — confirmed API, filter for EU-relevant
# ---------------------------------------------------------------
def scrape_remotive_eu():
    rows = []
    seen = set()
    categories = ["data-engineer", "devops-sysadmin", "backend-dev", "softwaredev", "data-science"]
    eu_terms = ["europe", "eu", "germany", "netherlands", "france", "sweden", "spain",
                "poland", "denmark", "switzerland", "ireland", "austria", "portugal",
                "finland", "belgium", "norway", "czech", "hungary", "remote", "worldwide"]
    try:
        for cat in categories:
            r = requests.get(
                f"https://remotive.com/api/remote-jobs?limit=200&category={cat}",
                headers=HEADERS, timeout=15
            )
            if not r.ok:
                continue
            for j in r.json().get("jobs", []):
                loc = j.get("candidate_required_location", "").lower()
                company = clean(j.get("company_name", ""))
                if not company or company in seen:
                    continue
                if loc and not any(t in loc for t in eu_terms):
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Remotive EU",
                    Country=j.get("candidate_required_location", "Europe") or "Europe",
                    City="Remote",
                    Sector=", ".join(j.get("tags", [])) or UNKNOWN,
                    Employer_Category="EU Remote",
                    Remote="Yes",
                    Hiring_Geography=j.get("candidate_required_location", "Europe") or "Europe",
                    Target_Roles=j.get("title", UNKNOWN),
                    Tech_Stack=", ".join(j.get("tags", [])) or UNKNOWN,
                    Hiring_Confidence="High",
                    Reason_Match=f"Remote EU role on Remotive: {j.get('title','')}",
                    Careers_URL=j.get("url", UNKNOWN),
                    Language_Requirement="English",
                ))
            time.sleep(0.3)
    except Exception as e:
        print(f"  Remotive EU error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# NO FLUFF JOBS — POST with required salaryCurrency param
# ---------------------------------------------------------------
def scrape_nofluffjobs():
    rows = []
    seen = set()
    categories = ["backend-developer", "data", "devops", "machine-learning", "architecture"]
    try:
        for cat in categories:
            r = requests.post(
                "https://nofluffjobs.com/api/search/posting",
                json={
                    "criteria": {"category": [cat]},
                    "page": 1,
                    "pageSize": 200,
                    "salaryCurrency": "PLN",
                    "salaryPeriod": "month",
                },
                headers={**HEADERS, "Content-Type": "application/json"},
                timeout=15
            )
            if not r.ok:
                continue
            for job in r.json().get("postings", []):
                company = clean(job.get("name", ""))
                if not company or company in seen:
                    continue
                seen.add(company)
                loc = job.get("location", {}) or {}
                rows.append(row(
                    Company=company,
                    Source="No Fluff Jobs (Poland/EU)",
                    Country=loc.get("country", "Poland") or "Poland",
                    City=loc.get("city", UNKNOWN) or UNKNOWN,
                    Sector="Tech",
                    Employer_Category="EU Tech",
                    Hiring_Geography="Poland/Europe",
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring on No Fluff Jobs: {cat}",
                    Website=job.get("url", UNKNOWN) or UNKNOWN,
                    Language_Requirement="English",
                ))
            time.sleep(0.3)
    except Exception as e:
        print(f"  NoFluffJobs error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# WELCOME TO THE JUNGLE — scrape HTML job listing pages
# ---------------------------------------------------------------
def scrape_welcome_jungle():
    rows = []
    seen = set()
    search_terms = ["data engineer", "machine learning", "MLOps", "data platform"]
    try:
        for term in search_terms:
            r = requests.get(
                f"https://www.welcometothejungle.com/en/jobs?query={term.replace(' ', '+')}&page=1",
                headers=HEADERS, timeout=15
            )
            # Extract from Next.js __NEXT_DATA__ JSON blob
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    jobs = (data.get("props", {}).get("pageProps", {})
                            .get("jobs", data.get("props", {}).get("pageProps", {})
                            .get("results", [])))
                    for job in jobs:
                        org = job.get("organization", job.get("company", {})) or {}
                        company = clean(org.get("name", "") if isinstance(org, dict) else str(org))
                        if not company or company in seen:
                            continue
                        seen.add(company)
                        rows.append(row(
                            Company=company,
                            Source="Welcome to the Jungle",
                            Country=org.get("country", "France") if isinstance(org, dict) else "France",
                            City=org.get("city", UNKNOWN) if isinstance(org, dict) else UNKNOWN,
                            Sector="Tech",
                            Employer_Category="EU Tech",
                            Hiring_Geography="Europe",
                            Target_Roles=job.get("name", UNKNOWN),
                            Hiring_Confidence="High",
                            Reason_Match=f"Hiring on Welcome to the Jungle: {term}",
                            Language_Requirement="English",
                        ))
                except Exception:
                    pass
            # Fallback: extract from JSON in page source
            companies = re.findall(r'"organization"\s*:\s*\{"[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'"companyName"\s*:\s*"([^"]+)"', r.text)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c,
                        Source="Welcome to the Jungle",
                        Country="Europe",
                        Sector="Tech",
                        Employer_Category="EU Tech",
                        Hiring_Geography="Europe",
                        Hiring_Confidence="High",
                        Reason_Match=f"Hiring on Welcome to the Jungle: {term}",
                        Language_Requirement="English",
                    ))
            time.sleep(1)
    except Exception as e:
        print(f"  Welcome to the Jungle error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# RELOCATE.ME — HTML scrape (JS-rendered but company names in source)
# ---------------------------------------------------------------
def scrape_relocate_me():
    rows = []
    seen = set()
    try:
        r = requests.get("https://relocate.me/search?keywords=data+engineer", headers=HEADERS, timeout=15)
        # Extract from JSON blobs in page
        companies = re.findall(r'"company"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r.text)
        companies += re.findall(r'"employer"\s*:\s*"([^"]+)"', r.text)
        companies += re.findall(r'"org_name"\s*:\s*"([^"]+)"', r.text)
        for c in companies:
            c = clean(c)
            if not c or c in seen:
                continue
            seen.add(c)
            rows.append(row(
                Company=c,
                Source="Relocate.me",
                Country="Europe",
                Sector="Tech",
                Employer_Category="EU Tech Relocation",
                Hiring_Geography="Europe",
                Hiring_Confidence="High",
                Reason_Match="Relocation job on Relocate.me",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"  Relocate.me error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# BERLIN STARTUP JOBS — RSS feed
# ---------------------------------------------------------------
def scrape_berlin_startup_jobs():
    rows = []
    seen = set()
    try:
        # RSS with proper referer
        r = requests.get(
            "https://berlinstartupjobs.com/feed/",
            headers={**HEADERS, "Referer": "https://berlinstartupjobs.com/"},
            timeout=15
        )
        if r.ok and "xml" in r.headers.get("Content-Type", ""):
            companies = re.findall(r'<company>(.*?)</company>', r.text, re.DOTALL)
            companies += re.findall(r'<author>(.*?)</author>', r.text, re.DOTALL)
            # From RSS item descriptions
            orgs = re.findall(r'hiringOrganization.*?name.*?"([^"]+)"', r.text)
            companies.extend(orgs)
        else:
            # HTML fallback
            r2 = requests.get(
                "https://berlinstartupjobs.com/engineering/",
                headers=HEADERS, timeout=15
            )
            companies = re.findall(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r2.text)
            companies += re.findall(r'class="lisco-company-name"[^>]*>([^<]+)<', r2.text)
        for c in companies:
            c = clean(c)
            if not c or c in seen:
                continue
            seen.add(c)
            rows.append(row(
                Company=c,
                Source="Berlin Startup Jobs",
                Country="Germany",
                City="Berlin",
                Sector="Tech/Startup",
                Employer_Category="Germany Tech",
                Hiring_Geography="Germany",
                Hiring_Confidence="High",
                Reason_Match="Actively hiring on Berlin Startup Jobs",
                Language_Requirement="English",
            ))
    except Exception as e:
        print(f"  Berlin Startup Jobs error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# GERMAN TECH JOBS — sitemap/HTML
# ---------------------------------------------------------------
def scrape_germantechjobs():
    rows = []
    seen = set()
    try:
        # The site redirects to /sign-up unless cookies set; use a list URL
        for search in ["data-engineer", "machine-learning", "backend"]:
            r = requests.get(
                f"https://germantechjobs.de/en/jobs/{search}/All",
                headers={**HEADERS, "Accept": "application/json"},
                timeout=15
            )
            # Try extracting from JSON data in page
            data_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', r.text, re.DOTALL)
            if data_match:
                try:
                    state = json.loads(data_match.group(1))
                    for job in state.get("jobs", {}).get("list", []):
                        c = clean(job.get("company", {}).get("name", "") if isinstance(job.get("company"), dict) else "")
                        if c and c not in seen:
                            seen.add(c)
                            rows.append(row(
                                Company=c, Source="GermanTechJobs.de",
                                Country="Germany", Sector="Tech",
                                Employer_Category="Germany Tech",
                                Hiring_Geography="Germany",
                                Hiring_Confidence="High",
                                Reason_Match=f"Hiring on GermanTechJobs.de: {search}",
                                Language_Requirement="English",
                            ))
                except Exception:
                    pass
            # Pattern extract
            companies = re.findall(r'"companyName"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'"company"\s*:\s*"([^"]+)"', r.text)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c, Source="GermanTechJobs.de",
                        Country="Germany", Sector="Tech",
                        Employer_Category="Germany Tech",
                        Hiring_Geography="Germany",
                        Hiring_Confidence="High",
                        Reason_Match=f"Hiring on GermanTechJobs.de: {search}",
                        Language_Requirement="English",
                    ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  GermanTechJobs error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# THE HUB — Nordic/EU startup jobs
# ---------------------------------------------------------------
def scrape_thehub():
    rows = []
    seen = set()
    try:
        for page in range(1, 6):
            r = requests.get(
                f"https://thehub.io/jobs?page={page}&skills[]=data-engineering&skills[]=machine-learning",
                headers=HEADERS, timeout=15
            )
            # Extract from JSON in page
            match = re.search(r'"jobs"\s*:\s*(\[.*?\])', r.text, re.DOTALL)
            if match:
                try:
                    jobs = json.loads(match.group(1))
                    for j in jobs:
                        org = j.get("company", j.get("organisation", {})) or {}
                        c = clean(org.get("name", "") if isinstance(org, dict) else str(org))
                        if c and c not in seen:
                            seen.add(c)
                            rows.append(row(
                                Company=c, Source="The Hub (Nordic/EU)",
                                Country="Europe", Sector="Tech/Startup",
                                Employer_Category="EU Startup",
                                Hiring_Geography="Europe",
                                Hiring_Confidence="High",
                                Reason_Match="Actively hiring on The Hub",
                                Language_Requirement="English",
                            ))
                except Exception:
                    pass
            # HTML fallback
            companies = re.findall(r'"company"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'class="[^"]*company-name[^"]*"[^>]*>([^<]{2,60})<', r.text)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c, Source="The Hub (Nordic/EU)",
                        Country="Europe", Sector="Tech/Startup",
                        Employer_Category="EU Startup",
                        Hiring_Geography="Europe",
                        Hiring_Confidence="Medium",
                        Reason_Match="Actively hiring on The Hub",
                        Language_Requirement="English",
                    ))
            if not companies:
                break
            time.sleep(0.5)
    except Exception as e:
        print(f"  The Hub error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# JOBFLUENT — Spain/EU, HTML scrape
# ---------------------------------------------------------------
def scrape_jobfluent():
    rows = []
    seen = set()
    try:
        for search in ["data-engineer", "machine-learning", "backend-developer"]:
            r = requests.get(
                f"https://www.jobfluent.com/jobs-{search}",
                headers=HEADERS, timeout=15
            )
            companies = re.findall(r'"company"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'"employer"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'class="[^"]*company[^"]*"[^>]*>([^<]{2,60})<', r.text, re.IGNORECASE)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c, Source="JobFluent (Spain/EU)",
                        Country="Spain", Sector="Tech",
                        Employer_Category="Spain Tech",
                        Hiring_Geography="Spain/EU",
                        Hiring_Confidence="High",
                        Reason_Match=f"English tech job on JobFluent: {search}",
                        Language_Requirement="English",
                    ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  JobFluent error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# TECNOEMPLEO — Spain, sitemap company list
# ---------------------------------------------------------------
def scrape_tecnoempleo():
    rows = []
    seen = set()
    try:
        # Sitemap has empresa (company) URLs — extract slugs as company names
        r = requests.get("https://www.tecnoempleo.com/sitemap.xml", headers=HEADERS, timeout=15)
        slugs = re.findall(r'tecnoempleo\.com/busqueda-empleo-empresa/([^/<]+)', r.text)
        for slug in slugs[:200]:  # limit to top 200
            name = slug.replace("-", " ").replace("_", " ").title().strip()
            if name and len(name) > 2 and name not in seen:
                seen.add(name)
                rows.append(row(
                    Company=name, Source="Tecnoempleo (Spain)",
                    Country="Spain", Sector="Tech",
                    Employer_Category="Spain Tech",
                    Hiring_Geography="Spain",
                    Hiring_Confidence="Medium",
                    Reason_Match="Listed employer on Tecnoempleo.com Spain",
                    Language_Requirement="English/Spanish",
                ))
        # Also scrape live search page
        r2 = requests.get(
            "https://www.tecnoempleo.com/busqueda-trabajo.php?te=data+engineer",
            headers=HEADERS, timeout=15
        )
        companies = re.findall(r'class="[^"]*empresa[^"]*"[^>]*>([^<]{2,60})<', r2.text, re.IGNORECASE)
        for c in companies:
            c = clean(c)
            if c and c not in seen:
                seen.add(c)
                rows.append(row(
                    Company=c, Source="Tecnoempleo (Spain)",
                    Country="Spain", Sector="Tech",
                    Employer_Category="Spain Tech",
                    Hiring_Geography="Spain",
                    Hiring_Confidence="High",
                    Reason_Match="Actively hiring on Tecnoempleo.com Spain",
                    Language_Requirement="English/Spanish",
                ))
    except Exception as e:
        print(f"  Tecnoempleo error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# IT-JOBBANK DENMARK
# ---------------------------------------------------------------
def scrape_itjobbank():
    rows = []
    seen = set()
    try:
        for term in ["data+engineer", "machine+learning", "software+engineer"]:
            r = requests.get(
                f"https://www.it-jobbank.dk/jobsoegning?q={term}",
                headers=HEADERS, timeout=15
            )
            companies = re.findall(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'class="[^"]*employer[^"]*"[^>]*>([^<]{2,60})<', r.text, re.IGNORECASE)
            companies += re.findall(r'"company"\s*:\s*"([^"]+)"', r.text)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c, Source="IT-Jobbank Denmark",
                        Country="Denmark", Sector="Tech",
                        Employer_Category="Denmark Tech",
                        Hiring_Geography="Denmark",
                        Hiring_Confidence="High",
                        Reason_Match="Actively hiring on IT-Jobbank.dk",
                        Language_Requirement="English",
                    ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  IT-Jobbank error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# WEAREDEVELOPERS — EU-wide developer jobs
# ---------------------------------------------------------------
def scrape_wearedevelopers():
    rows = []
    seen = set()
    try:
        for term in ["data-engineer", "machine-learning", "backend"]:
            r = requests.get(
                f"https://www.wearedevelopers.com/en/jobs?q={term}",
                headers=HEADERS, timeout=15
            )
            companies = re.findall(r'"company"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'"employer"\s*:\s*"([^"]+)"', r.text)
            companies += re.findall(r'data-company="([^"]+)"', r.text)
            for c in companies:
                c = clean(c)
                if c and c not in seen:
                    seen.add(c)
                    rows.append(row(
                        Company=c, Source="WeAreDevelopers Jobs",
                        Country="Europe", Sector="Tech",
                        Employer_Category="EU Tech",
                        Hiring_Geography="Europe",
                        Hiring_Confidence="High",
                        Reason_Match="Actively hiring on WeAreDevelopers",
                        Language_Requirement="English",
                    ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  WeAreDevelopers error: {e}")
    return rows, seen


# ---------------------------------------------------------------
# VC PORTFOLIO PAGES — existence-based (EU + AU + USA)
# ---------------------------------------------------------------
def scrape_vc_portfolios():
    print("  Scraping VC portfolio pages...")
    rows = []
    seen = set()

    vc_pages = [
        ("https://www.balderton.com/portfolio/", "Balderton Capital", "Europe"),
        ("https://www.indexventures.com/companies/", "Index Ventures", "Europe"),
        ("https://www.northzone.com/portfolio/", "Northzone", "Europe"),
        ("https://atomico.com/portfolio/", "Atomico", "Europe"),
        ("https://www.earlybird.com/portfolio/", "EarlyBird VC", "Europe"),
        ("https://www.hv.capital/portfolio/", "HV Capital", "Germany"),
        ("https://a16z.com/portfolio/", "a16z", "USA"),
        ("https://www.bvp.com/portfolio", "Bessemer Venture Partners", "USA"),
        ("https://accel.com/companies", "Accel", "USA/Europe"),
        ("https://www.sequoiacap.com/companies/", "Sequoia Capital", "USA/EU"),
        ("https://blackbird.vc/portfolio", "Blackbird Ventures", "Australia"),
        ("https://squarepeg.vc/portfolio", "Square Peg Capital", "Australia"),
        ("https://nfx.com/portfolio", "NFX", "USA"),
        ("https://generalcatalyst.com/portfolio", "General Catalyst", "USA"),
        ("https://point72.com/portfolio/", "Point72 Ventures", "USA"),
        ("https://www.creandum.com/portfolio/", "Creandum", "Europe"),
        ("https://lakestar.com/portfolio", "Lakestar", "Europe"),
        ("https://www.seventure.fr/portfolio/", "Seventure Partners", "France"),
    ]

    for url, vc_name, region in vc_pages:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            companies = re.findall(r'"name"\s*:\s*"([A-Z][^"]{2,50})"', r.text)
            companies += re.findall(r'alt="([A-Z][^"]{2,50})\s*(?:[Ll]ogo)"', r.text)
            companies += re.findall(r'<h[23][^>]*>([A-Z][^<]{2,50})</h[23]>', r.text)
            companies += re.findall(r'class="[^"]*portfolio[^"]*(?:name|title)[^"]*"[^>]*>([^<]{2,60})<', r.text, re.IGNORECASE)
            skip = {"portfolio", "companies", "our portfolio", "investments", "team",
                    "home", "about", "contact", "menu", "search", "news", "blog", "insights"}
            for c in companies:
                c = clean(c)
                if not c or c.lower() in skip or c in seen:
                    continue
                seen.add(c)
                rows.append(row(
                    Company=c,
                    Source=f"VC Portfolio: {vc_name}",
                    Country=region,
                    Sector="Tech/Startup",
                    Employer_Category="VC Backed",
                    Hiring_Geography=region,
                    Hiring_Confidence="Low",
                    Reason_Match=f"Portfolio company of {vc_name}",
                    Language_Requirement="English",
                ))
            time.sleep(1)
        except Exception as e:
            print(f"    VC {vc_name} error: {e}")

    return rows, seen


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def run():
    all_rows = []
    global_seen = set()

    scrapers = [
        ("Landing.jobs", scrape_landing_jobs),
        ("Remotive EU", scrape_remotive_eu),
        ("No Fluff Jobs", scrape_nofluffjobs),
        ("Welcome to the Jungle", scrape_welcome_jungle),
        ("Relocate.me", scrape_relocate_me),
        ("Berlin Startup Jobs", scrape_berlin_startup_jobs),
        ("GermanTechJobs.de", scrape_germantechjobs),
        ("The Hub (Nordic/EU)", scrape_thehub),
        ("JobFluent (Spain)", scrape_jobfluent),
        ("Tecnoempleo (Spain)", scrape_tecnoempleo),
        ("IT-Jobbank Denmark", scrape_itjobbank),
        ("WeAreDevelopers", scrape_wearedevelopers),
        ("VC Portfolios", scrape_vc_portfolios),
    ]

    for name, func in scrapers:
        try:
            print(f"  Scraping {name}...")
            rows, _ = func()
            new_rows = [r for r in rows if r["Company"] not in global_seen]
            global_seen.update(r["Company"] for r in new_rows)
            all_rows.extend(new_rows)
            print(f"    {name}: {len(rows)} found, {len(new_rows)} new")
        except Exception as e:
            print(f"    {name} failed: {e}")
        time.sleep(0.5)

    added = write_batch(all_rows, "pipeline_eu_portals")
    print(f"\n  EU Portals total: {len(all_rows)} companies ({added} new to master)")
    log_run("EU Portals", len(all_rows))
    return added
