"""
Classify scraped rows as company profiles vs live job signals.
All sources stay in the pipeline — nothing is dropped, only routed.
"""
import re

UNKNOWN = "Unknown"

JOB_URL_PATTERNS = (
    r"indeed\.com/viewjob",
    r"linkedin\.com/jobs/view",
    r"glassdoor\.[a-z]+/job",
    r"seek\.com\.au/job",
    r"seek\.co\.nz/job",
    r"adzuna\.[a-z.]+/details",
    r"jora\.com/au/job",
    r"careerone\.com\.au/job",
    r"naukri\.com/job-listings",
    r"naukri\.com/.*-jobs-",
)

JUNK_WEBSITE_DOMAINS = {
    "indeed.com", "au.indeed.com", "in.indeed.com", "nz.indeed.com",
    "uk.indeed.com", "de.indeed.com", "fr.indeed.com", "ca.indeed.com",
    "linkedin.com", "au.linkedin.com", "in.linkedin.com",
    "builtin.com", "builtinnyc.com", "builtinsf.com", "glassdoor.com",
    "remoteok.com", "remotive.com", "seek.com.au", "seek.co.nz",
    "adzuna.com.au", "adzuna.co.nz", "jora.com", "careerone.com.au",
    "dice.com", "naukri.com",
}

COMPANY_SOURCE_MARKERS = (
    "yc directory", "h1b", "static_list", "static list", "scaling europe",
    "vc portfolio", "remoteok api", "remotive api", "remotive eu",
    "github api", "github signal", "built in", "dice.com usa",
    "producthunt", "f6s", "govhack", "landing.jobs", "no fluff jobs",
    "welcome to the jungle", "relocate.me", "berlin startup jobs",
    "germantechjobs", "the hub", "jobfluent", "tecnoempleo", "it-jobbank",
    "wearedevelopers", "naukri seed", "naukri sitemap", "ai research batch",
    "euroboom", "eu startup",
)


def _blank(val: str) -> bool:
    if not val:
        return True
    return val.strip().lower() in ("", "unknown", "none", "not found", "n/a")


def is_job_posting_url(url: str) -> bool:
    if not url or _blank(url):
        return False
    lower = url.lower()
    return any(re.search(p, lower) for p in JOB_URL_PATTERNS)


def website_domain(website: str) -> str:
    if _blank(website):
        return ""
    url = website.lower().strip()
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    domain = url.split("/")[0].strip()
    if domain in JUNK_WEBSITE_DOMAINS:
        return ""
    return domain


def classify_record(row: dict) -> str:
    """Return 'company' or 'job_signal'."""
    source = (row.get("Source") or "").lower()
    careers = row.get("Careers_URL") or ""
    website = row.get("Website") or ""
    reason = (row.get("Reason_Match") or "").lower()

    if any(marker in source for marker in COMPANY_SOURCE_MARKERS):
        return "company"

    domain = website_domain(website)
    if domain:
        return "company"

    if is_job_posting_url(careers):
        return "job_signal"

    if reason.startswith("actively hiring"):
        return "job_signal"

    if "hn who is hiring" in source:
        return "company"

    if any(s in source for s in ("indeed", "linkedin", "seek ", "adzuna", "jora")):
        return "job_signal"

    return "company"