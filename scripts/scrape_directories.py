"""
Large-scale directory scrapers to hit 5k-20k employer target.
Sources:
1. Hacker News "Who is Hiring" (Algolia API, free, no auth) - global tech companies
2. Australia/NZ - Indeed + LinkedIn via JobSpy
3. USA Tier 2/3 cities - Indeed via JobSpy
4. EU broader coverage - Remotive + JobSpy EU cities
5. Papers With Code institutions - AI/ML companies
6. GitHub trending organizations - tech signal
"""
import csv, os, re, requests, time, sys, signal
from datetime import datetime


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

sys.path.insert(0, os.path.dirname(__file__))
from schema import FIELDS, UNKNOWN
from validate import append_batch
from pipeline_log import log_run

BASE = os.path.join(os.path.dirname(__file__), "..")
BATCH_DIR = os.path.join(BASE, "batches")


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
    return added


# --- 1. Hacker News "Who is Hiring" ---
def scrape_hn_hiring():
    print("Scraping HN Who is Hiring...")
    rows = []
    seen = set()

    try:
        # Get the latest "Who is Hiring" threads
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": "Who is hiring",
                "tags": "ask_hn,story",
                "hitsPerPage": 5
            },
            timeout=15
        )
        threads = [h for h in r.json().get("hits", []) if "hiring" in h.get("title", "").lower()]

        for thread in threads[:3]:  # last 3 months
            story_id = thread["objectID"]
            # Get comments from this thread
            r2 = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "tags": f"comment,story_{story_id}",
                    "hitsPerPage": 1000
                },
                timeout=15
            )
            comments = r2.json().get("hits", [])

            for comment in comments:
                text = comment.get("comment_text", "") or ""
                text = re.sub(r'<[^>]+>', ' ', text)

                # Extract company name - usually first line or "Company | Location | ..."
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue

                first_line = lines[0]
                # Pattern: "CompanyName | Location | Remote | ..."
                parts = [p.strip() for p in re.split(r'\|', first_line)]
                company = parts[0].strip() if parts else ""

                # Clean up
                company = re.sub(r'<[^>]+>', '', company).strip()
                company = re.sub(r'\(.*?\)', '', company).strip()
                if not company or len(company) > 60 or len(company) < 2:
                    continue
                if company.lower().startswith(("http", "we are", "we're", "i am", "looking")):
                    continue
                if company in seen:
                    continue
                seen.add(company)

                # Extract location and remote hints
                location = parts[1].strip() if len(parts) > 1 else UNKNOWN
                remote = "Yes" if any("remote" in p.lower() for p in parts) else "Unknown"

                # Detect country from location
                country = UNKNOWN
                loc_lower = location.lower()
                if any(c in loc_lower for c in ["uk", "london", "manchester", "edinburgh"]):
                    country = "UK"
                elif any(c in loc_lower for c in ["germany", "berlin", "munich", "hamburg"]):
                    country = "Germany"
                elif any(c in loc_lower for c in ["netherlands", "amsterdam", "rotterdam"]):
                    country = "Netherlands"
                elif any(c in loc_lower for c in ["france", "paris", "lyon"]):
                    country = "France"
                elif any(c in loc_lower for c in ["usa", "us", "new york", "san francisco", "seattle", "austin", "boston"]):
                    country = "USA"
                elif any(c in loc_lower for c in ["australia", "sydney", "melbourne"]):
                    country = "Australia"
                elif any(c in loc_lower for c in ["canada", "toronto", "vancouver"]):
                    country = "Canada"
                elif any(c in loc_lower for c in ["sweden", "stockholm"]):
                    country = "Sweden"
                elif any(c in loc_lower for c in ["ireland", "dublin"]):
                    country = "Ireland"
                elif "remote" in loc_lower:
                    country = "Remote"

                rows.append(row(
                    Company=company,
                    Source="HN Who is Hiring",
                    Country=country,
                    City=location[:50],
                    Sector="Tech",
                    Employer_Category="HN Hiring",
                    Remote=remote,
                    Hiring_Geography=location[:50],
                    Hiring_Confidence="High",
                    Reason_Match=f"Actively hiring on HN: {first_line[:80]}",
                    Language_Requirement="English",
                ))
            time.sleep(0.5)

    except Exception as e:
        print(f"  HN error: {e}")

    write_batch(rows, "pipeline_hn_hiring")
    print(f"  HN Who is Hiring: {len(rows)} companies")
    log_run("HN Who is Hiring", len(rows))
    return len(rows)


# --- 2. Australia / NZ ---
def scrape_australia_nz():
    print("Scraping Australia/NZ...")
    try:
        from jobspy import scrape_jobs
        rows = []
        seen = set()

        searches = [
            # Australia — Tier 1
            ("data engineer OR AI engineer OR machine learning", "Sydney, Australia", "Australia"),
            ("data engineer OR AI engineer OR machine learning", "Melbourne, Australia", "Australia"),
            # Australia — Tier 2
            ("data engineer OR AI engineer", "Brisbane, Australia", "Australia"),
            ("data engineer OR AI engineer", "Perth, Australia", "Australia"),
            ("data engineer OR AI engineer", "Adelaide, Australia", "Australia"),
            ("data engineer OR software engineer", "Canberra, Australia", "Australia"),
            # Australia — Tier 3
            ("data engineer OR software engineer", "Gold Coast, Australia", "Australia"),
            ("data engineer OR software engineer", "Newcastle, Australia", "Australia"),
            ("data engineer OR software engineer", "Wollongong, Australia", "Australia"),
            ("data engineer OR software engineer", "Hobart, Australia", "Australia"),
            ("data engineer OR software engineer", "Darwin, Australia", "Australia"),
            ("data engineer OR software engineer", "Sunshine Coast, Australia", "Australia"),
            # New Zealand — Tier 1
            ("data engineer OR AI engineer", "Auckland, New Zealand", "New Zealand"),
            # New Zealand — Tier 2
            ("data engineer OR AI engineer", "Wellington, New Zealand", "New Zealand"),
            ("data engineer OR software engineer", "Christchurch, New Zealand", "New Zealand"),
            # New Zealand — Tier 3
            ("data engineer OR software engineer", "Hamilton, New Zealand", "New Zealand"),
            ("data engineer OR software engineer", "Dunedin, New Zealand", "New Zealand"),
            ("data engineer OR software engineer", "Tauranga, New Zealand", "New Zealand"),
        ]

        for term, location, country in searches:
            try:
                print(f"    AU/NZ: {location}")
                jobs = with_timeout(45, scrape_jobs,
                    site_name=["indeed", "linkedin"],
                    search_term=term,
                    location=location,
                    results_wanted=50,
                    hours_old=72,
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
                        Source=f"Indeed/LinkedIn {country}",
                        Country=country,
                        City=location.split(",")[0],
                        Sector="Tech",
                        Employer_Category=f"{country} Tech",
                        Remote="Unknown",
                        Hiring_Geography=country,
                        Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring in {location}",
                        Website=UNKNOWN,
                        Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                        Language_Requirement="English",
                    ))
                time.sleep(2)
            except Exception:
                pass

        write_batch(rows, "pipeline_aunz")
        print(f"  Australia/NZ: {len(rows)} companies")
        log_run("Australia/NZ", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  Australia/NZ error: {e}")
        return 0


# --- 3. USA Tier 2/3 cities ---
def scrape_usa_tier2():
    print("Scraping USA Tier 2/3 cities...")
    try:
        from jobspy import scrape_jobs
        rows = []
        seen = set()

        cities = [
            # Tier 2 — established secondary tech hubs
            ("Austin, TX", "USA"), ("Denver, CO", "USA"), ("Chicago, IL", "USA"),
            ("Atlanta, GA", "USA"), ("Boston, MA", "USA"), ("Miami, FL", "USA"),
            ("Portland, OR", "USA"), ("Nashville, TN", "USA"), ("Salt Lake City, UT", "USA"),
            ("Raleigh, NC", "USA"), ("Pittsburgh, PA", "USA"), ("Minneapolis, MN", "USA"),
            ("Phoenix, AZ", "USA"), ("Dallas, TX", "USA"), ("Detroit, MI", "USA"),
            ("Charlotte, NC", "USA"), ("San Diego, CA", "USA"), ("San Jose, CA", "USA"),
            ("Bellevue, WA", "USA"), ("Sacramento, CA", "USA"), ("Tampa, FL", "USA"),
            ("Orlando, FL", "USA"), ("Kansas City, MO", "USA"), ("Cincinnati, OH", "USA"),
            ("Columbus, OH", "USA"), ("Indianapolis, IN", "USA"), ("Cleveland, OH", "USA"),
            # Tier 3 — rising & hidden regional ecosystems
            ("Provo, UT", "USA"), ("Boise, ID", "USA"), ("Madison, WI", "USA"),
            ("Milwaukee, WI", "USA"), ("Louisville, KY", "USA"), ("Richmond, VA", "USA"),
            ("Oklahoma City, OK", "USA"), ("Tulsa, OK", "USA"), ("Omaha, NE", "USA"),
            ("Des Moines, IA", "USA"), ("San Antonio, TX", "USA"), ("Jacksonville, FL", "USA"),
            ("Huntsville, AL", "USA"), ("New Orleans, LA", "USA"), ("Hartford, CT", "USA"),
            ("Providence, RI", "USA"), ("Buffalo, NY", "USA"), ("Rochester, NY", "USA"),
            ("Las Vegas, NV", "USA"), ("Tucson, AZ", "USA"), ("Colorado Springs, CO", "USA"),
            ("Spokane, WA", "USA"), ("Albuquerque, NM", "USA"), ("Memphis, TN", "USA"),
            ("Fargo, ND", "USA"), ("Sioux Falls, SD", "USA"), ("Honolulu, HI", "USA"),
        ]

        for city, country in cities:
            try:
                print(f"    USA: {city}")
                jobs = with_timeout(45, scrape_jobs,
                    site_name=["indeed"],
                    search_term="data engineer OR AI engineer OR machine learning",
                    location=city,
                    results_wanted=30,
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
                        Source=f"Indeed USA ({city})",
                        Country=country,
                        City=city.split(",")[0],
                        Sector="Tech",
                        Employer_Category="USA Tech",
                        Hiring_Geography="USA",
                        Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring in {city}",
                        Website=UNKNOWN,
                        Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                        Language_Requirement="English",
                    ))
                time.sleep(2)
            except Exception as e:
                print(f"    Error {city}: {e}")

        write_batch(rows, "pipeline_usa_tier2")
        print(f"  USA Tier 2/3: {len(rows)} companies")
        log_run("USA Tier 2/3", len(rows))
        return len(rows)
    except Exception as e:
        print(f"  USA Tier 2/3 error: {e}")
        return 0


# --- 4. EU cities via Remotive (faster, no rate limits) + JobSpy for top 5 only ---
def scrape_eu_cities():
    print("Scraping EU cities...")
    rows = []
    seen = set()

    # Remotive EU - already covered in run_scrapers.py but get more by searching specific terms
    eu_terms = [
        "germany", "netherlands", "sweden", "ireland", "france",
        "spain", "portugal", "poland", "austria", "denmark"
    ]
    try:
        for term in eu_terms:
            r = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": term, "limit": "100"},
                timeout=15
            )
            for j in r.json().get("jobs", []):
                loc = j.get("candidate_required_location", "")
                company = j.get("company_name", "")
                if not company or company in seen:
                    continue
                seen.add(company)
                rows.append(row(
                    Company=company,
                    Source="Remotive EU",
                    Country=term.title(),
                    City="Remote",
                    Sector=", ".join(j.get("tags", [])) or UNKNOWN,
                    Employer_Category="EU Tech",
                    Remote="Yes",
                    Hiring_Geography=loc or term.title(),
                    Target_Roles=j.get("title", UNKNOWN),
                    Hiring_Confidence="High",
                    Reason_Match=f"Hiring remotely in {term}",
                    Careers_URL=j.get("url", UNKNOWN),
                    Language_Requirement="English",
                ))
            time.sleep(0.5)
    except Exception as e:
        print(f"  Remotive EU error: {e}")

    # JobSpy for 45+ EU cities across 20+ countries — tier 1/2/3
    try:
        from jobspy import scrape_jobs
        top_cities = [
            # Germany (tier 1 + tier 2 + tier 3)
            ("Berlin", "Germany"), ("Munich", "Germany"), ("Hamburg", "Germany"),
            ("Frankfurt", "Germany"), ("Cologne", "Germany"), ("Stuttgart", "Germany"),
            ("Leipzig", "Germany"), ("Düsseldorf", "Germany"), ("Dresden", "Germany"),
            # Netherlands
            ("Amsterdam", "Netherlands"), ("Rotterdam", "Netherlands"),
            ("Eindhoven", "Netherlands"), ("Utrecht", "Netherlands"),
            # France
            ("Paris", "France"), ("Lyon", "France"), ("Toulouse", "France"),
            ("Bordeaux", "France"), ("Nantes", "France"), ("Marseille", "France"),
            # Poland
            ("Warsaw", "Poland"), ("Krakow", "Poland"), ("Wroclaw", "Poland"), ("Gdansk", "Poland"),
            # Czech Republic
            ("Prague", "Czech Republic"), ("Brno", "Czech Republic"),
            # Austria
            ("Vienna", "Austria"), ("Graz", "Austria"),
            # Sweden
            ("Stockholm", "Sweden"), ("Gothenburg", "Sweden"), ("Malmö", "Sweden"),
            # Denmark
            ("Copenhagen", "Denmark"), ("Aarhus", "Denmark"),
            # Finland
            ("Helsinki", "Finland"), ("Tampere", "Finland"),
            # Belgium
            ("Brussels", "Belgium"), ("Ghent", "Belgium"), ("Antwerp", "Belgium"),
            # Switzerland
            ("Zurich", "Switzerland"), ("Basel", "Switzerland"), ("Geneva", "Switzerland"),
            # Norway
            ("Oslo", "Norway"), ("Bergen", "Norway"),
            # Ireland
            ("Dublin", "Ireland"), ("Cork", "Ireland"), ("Galway", "Ireland"),
            # Portugal
            ("Lisbon", "Portugal"), ("Porto", "Portugal"), ("Braga", "Portugal"),
            # Spain
            ("Madrid", "Spain"), ("Barcelona", "Spain"), ("Valencia", "Spain"),
            ("Bilbao", "Spain"), ("Málaga", "Spain"),
            # Italy
            ("Milan", "Italy"), ("Rome", "Italy"), ("Turin", "Italy"), ("Bologna", "Italy"),
            # Romania
            ("Bucharest", "Romania"), ("Cluj-Napoca", "Romania"),
            # Baltic states
            ("Tallinn", "Estonia"), ("Riga", "Latvia"), ("Vilnius", "Lithuania"),
            # Balkans + Central
            ("Budapest", "Hungary"), ("Zagreb", "Croatia"),
            ("Sofia", "Bulgaria"), ("Athens", "Greece"), ("Bratislava", "Slovakia"),
            # Small but strong tech hubs
            ("Luxembourg City", "Luxembourg"),
        ]
        for city, country in top_cities:
            try:
                print(f"    EU: {city}")
                jobs = with_timeout(45, scrape_jobs,
                    site_name=["indeed"],
                    search_term="data engineer OR AI engineer OR machine learning",
                    location=f"{city}, {country}",
                    results_wanted=30,
                    hours_old=72,
                    country_indeed=country
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
                        Source=f"Indeed EU ({city})",
                        Country=country,
                        City=city,
                        Sector="Tech",
                        Employer_Category="EU Tech",
                        Hiring_Geography=f"{city}, {country}",
                        Target_Roles=str(j.get("title", UNKNOWN) or UNKNOWN),
                        Hiring_Confidence="High",
                        Reason_Match=f"Actively hiring in {city}",
                        Website=UNKNOWN,
                        Careers_URL=str(j.get("job_url", UNKNOWN) or UNKNOWN),
                        Language_Requirement="English",
                    ))
                time.sleep(2)
            except Exception as e:
                print(f"    Error {city}: {e}")
    except Exception as e:
        print(f"  EU JobSpy error: {e}")

    write_batch(rows, "pipeline_eu_cities")
    print(f"  EU cities: {len(rows)} companies")
    log_run("EU Cities", len(rows))
    return len(rows)


# --- 5. GitHub trending orgs (AI/ML signal) ---
def scrape_github_orgs():
    print("Scraping GitHub orgs (AI/ML/Data stack signal)...")
    seen = set()
    rows = []

    queries = [
        "LLM inference production python stars:>50",
        "RAG retrieval augmented generation python stars:>30",
        "data platform dbt spark python stars:>30",
        "MLOps machine learning platform stars:>50",
        "AI governance compliance python stars:>20",
        "geospatial analytics python stars:>30",
        "fintech infrastructure golang python stars:>50",
        "smart city urban analytics python stars:>20",
        "climate data analytics python stars:>20",
        "legal tech NLP python stars:>20",
    ]

    for q in queries:
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "updated", "per_page": "50"},
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "employer-discovery"},
                timeout=15
            )
            for repo in r.json().get("items", []):
                owner = repo.get("owner", {})
                if owner.get("type") != "Organization":
                    continue
                org = owner.get("login", "")
                if not org or org in seen:
                    continue
                seen.add(org)
                rows.append(row(
                    Company=org,
                    Source="GitHub Stack Signal",
                    Website=f"https://github.com/{org}",
                    Sector="AI Infrastructure / Tech",
                    Employer_Category="GitHub Signal",
                    Target_Roles="AI Engineer / Data Engineer",
                    Tech_Stack=repo.get("language", UNKNOWN),
                    Hiring_Confidence="Low",
                    Reason_Match=f"Active GitHub org: {repo.get('full_name','')} ({q.split()[0]})",
                    Language_Requirement="English",
                ))
            time.sleep(1)
        except Exception:
            pass

    write_batch(rows, "pipeline_github_orgs")
    print(f"  GitHub orgs: {len(rows)} companies")
    log_run("GitHub Orgs", len(rows))
    return len(rows)


def run():
    total = 0
    total += scrape_hn_hiring()
    total += scrape_australia_nz()
    total += scrape_usa_tier2()
    total += scrape_eu_cities()
    total += scrape_github_orgs()
    print(f"\nDirectory scrapers total: {total} new companies")
    return total


if __name__ == "__main__":
    run()
