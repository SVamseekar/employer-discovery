"""
Phase 4 enrichment: For each company in the shortlist, find:
1. Open Data/AI/Engineer job postings (via JobSpy)
2. LinkedIn company page URL
3. Generate cold email draft
Output: data/enriched_shortlist.csv
"""
import csv, os, time, re, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from candidate_profile import CANDIDATE, SIGNATURE, get_best_project, get_skill_overlap, get_visa_line, get_language_line

BASE = os.path.join(os.path.dirname(__file__), "..")
SHORTLIST = os.path.join(BASE, "data", "cold_outreach_shortlist.csv")
ENRICHED = os.path.join(BASE, "data", "enriched_shortlist.csv")


def find_open_jobs(company, careers_url):
    """Search Indeed for open roles at this company."""
    try:
        from jobspy import scrape_jobs
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=f"data engineer OR AI engineer OR machine learning engineer",
            location="",
            results_wanted=5,
            hours_old=30,
            country_indeed="worldwide"
        )
        # Filter by company name
        company_jobs = jobs[jobs["company"].str.lower().str.contains(
            company.lower()[:15], na=False
        )]
        if len(company_jobs):
            titles = company_jobs["title"].tolist()[:3]
            urls = company_jobs["job_url"].tolist()[:1]
            return "; ".join(titles), urls[0] if urls else careers_url
    except Exception:
        pass
    return "", careers_url


_INDIA_TERMS = {"india", "hyderabad", "bangalore", "bengaluru", "mumbai", "pune",
                "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata"}


def _subject(company: str, country: str) -> str:
    if any(t in country.lower() for t in _INDIA_TERMS):
        return f"AI/Data Engineer — {company} | Hyderabad-Based, Immediate Joiner"
    return f"AI/Data Engineer — {company} | EU Blue Card Eligible"


def generate_email(company, sector, tech_stack, open_role, match_notes,
                   country="", remote="", language_req=""):
    """Generate a tailored cold email using CV data from candidate_profile.py."""
    project       = get_best_project(sector, match_notes, tech_stack)
    skill_overlap = get_skill_overlap(tech_stack)
    visa_line     = get_visa_line(country, remote=remote)
    lang_line     = get_language_line(language_req)

    role_line = f"regarding the {open_role} role" if open_role else "about potential AI/Data Engineering opportunities"
    role_intro = f"I'm reaching out {role_line}."

    if skill_overlap:
        tech_mention = f"I noticed your stack includes {', '.join(skill_overlap[:3])} — tools I use daily in production."
    elif tech_stack and tech_stack not in ("Unknown", ""):
        tech_mention = f"Your work in {sector} maps closely to what I've been building."
    else:
        tech_mention = f"Your focus on {sector} aligns with my portfolio."

    lang_block = f"\n{lang_line}\n" if lang_line else ""

    email = f"""Subject: {_subject(company, country)}

Hi {company} Team,

I came across {company} while researching {sector} companies and wanted to reach out directly.

{role_intro} {tech_mention}

One example of my work: {project['one_liner']}.

My current stack: Python, Java 17/Spring Boot 3, Databricks, dbt, GCP, Azure Data Factory, Kubernetes — all used in production at an institutional fintech in London.

{visa_line}
{lang_block}
Would you be open to a 20-minute call to see if there's a fit?

{SIGNATURE}"""

    return email.strip()


def run():
    rows = []
    with open(SHORTLIST, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        shortlist_fields = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f"Enriching {len(rows)} companies...")

    enriched_fields = shortlist_fields + [
        "Open_Roles_Found", "Best_Job_URL", "LinkedIn_Company",
        "Cold_Email_Draft", "Enriched_At"
    ]

    enriched = []
    for i, row in enumerate(rows):
        company = row["Company"]
        print(f"  [{i+1:3d}/{len(rows)}] {company[:40]}")

        # Find open jobs (only for top 30 to avoid rate limits)
        open_roles, job_url = "", row.get("Careers_URL", "")
        if i < 30:
            open_roles, job_url = find_open_jobs(company, row.get("Careers_URL", ""))
            time.sleep(1)

        # LinkedIn company URL (constructed from name)
        linkedin_slug = re.sub(r"[^a-z0-9]", "-", company.lower()).strip("-")
        linkedin_url = f"https://www.linkedin.com/company/{linkedin_slug}"

        # Cold email
        email = generate_email(
            company=company,
            sector=row.get("Sector", "tech"),
            tech_stack=row.get("Tech_Stack", ""),
            open_role=open_roles.split(";")[0].strip() if open_roles else "",
            match_notes=row.get("Match_Notes", ""),
            country=row.get("Country", ""),
            remote=row.get("Remote", ""),
            language_req=row.get("Language_Requirement", ""),
        )

        out = dict(row)
        out["Open_Roles_Found"] = open_roles
        out["Best_Job_URL"] = job_url
        out["LinkedIn_Company"] = linkedin_url
        out["Cold_Email_Draft"] = email
        out["Enriched_At"] = datetime.now().strftime("%Y-%m-%d")
        enriched.append(out)

    with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=enriched_fields)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"\nDone. Enriched shortlist: {ENRICHED}")
    print(f"Open roles found for top 30 companies.")


if __name__ == "__main__":
    run()
