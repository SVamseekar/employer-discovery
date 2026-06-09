# Global Employer Discovery System — What We Built

**Project:** employer-discovery  
**Owner:** Marti Soura Vamseekar (martisoura@gmail.com)  
**Goal:** Build a database of 5,000–20,000 global employers to apply to as an AI/Data Engineer seeking EU relocation, then send personalized cold emails to the best matches.

---

## Who You Are (context baked into the system)

- AI/Data Engineer at Innosolv London (institutional fintech, remote from Hyderabad)
- MSc Data Science, University of Greenwich
- EU Blue Card eligible — no employer pre-registration needed for 28 EU countries
- Target countries: Germany, Netherlands, Ireland, France, Sweden, Austria, Denmark, Finland, Belgium, Switzerland
- Current stack: Python, Java 17/Spring Boot 3, Databricks, dbt, GCP, Azure Data Factory, Kubernetes
- Certifications: Microsoft Azure Data Engineer Associate (DP-203, March 2025)

---

## The 6-Phase Pipeline

| Phase | Script | What it does |
|-------|--------|-------------|
| 1 | `run_scrapers.py` | Pulls companies from all sources → writes batch CSVs |
| 2 | `validate.py` | Deduplicates batches → appends new rows to master CSV |
| 3 | `visa_crossref.py` | Cross-references visa registers → flags sponsors |
| 4 | `score_shortlist.py` | Scores every company → picks top 100 |
| 5 | `enrich_shortlist.py` | Finds open jobs + generates cold emails |
| 6 | `send_outreach.py` | Sends emails via Gmail API |

---

## Every Script and What It Does

### `candidate_profile.py`
Single source of truth for your CV. All other scripts import from this.
- `CANDIDATE` dict: name, email, linkedin, github, phone, location, visa status, role targets, education, certifications, skills (6 groups), projects (5)
- `get_best_project(sector, reason, tech_stack)` — picks most thematically relevant project for a company
- `get_skill_overlap(tech_stack)` — finds your CV skills in the company's stack
- `get_visa_line(country, remote)` — returns correct visa/relocation sentence (EU Blue Card for EU companies, remote line for remote-only)
- `get_language_line(language_req)` — handles Dutch/German language requirements
- **Edit this when:** you change jobs, get a new cert, change target countries, or your contact details change

### `run_scrapers.py`
Master orchestrator. Calls all scrapers in sequence, then runs validate, visa_crossref, and score_shortlist automatically.
- Includes a daily 2pm cron (configured on your machine)

### `scrape_directories.py`
Primary EU + global company sources:
- YC company API (Y Combinator batch companies)
- RemoteOK API
- Remotive API
- EU Startups directory
- Scaling Europe Substack
- Crunchbase/Dealroom EU equivalents
- H1B sponsor XLSX (import_h1b.py)
- HN Algolia (Hacker News Who is Hiring)
- **44 USA cities** (expanded from 15)
- **66 EU cities** across 20+ countries

### `scrape_usa_aunz.py` *(new — built this session)*
Comprehensive USA + AU/NZ coverage:
- **USA via JobSpy:** 22 cities (Tier 1: NYC, SF, LA, Seattle, Chicago, DC, Boston + 15 more Tier 2/3 cities)
- **Dice.com** USA tech jobs
- **Built In** — 13 city hubs (SF, NYC, LA, Chicago, Boston, Austin, Denver, Seattle, Atlanta, Miami, Portland, SLC, Raleigh)
- **F6S, ProductHunt** USA tech directories
- **RemoteOK** filtered for USA
- **HN Who is Hiring** USA filter
- **AU:** Seek (6 cities), Adzuna, Jora, CareerOne, 9 AU/NZ cities via JobSpy
- **NZ:** Seek NZ (3 cities), Adzuna NZ
- **AU tech directories:** StartupAus, Stone & Chalk, GovHack
- Note: Seek/Adzuna/Jora all block bots and return 0 — JobSpy via Indeed AU is the reliable source

### `scrape_eu_portals.py` *(new — built this session)*
80 EU portals from europe_it_job_portals.xlsx + 18 VC portfolio scrapers:
- **Landing.jobs** `/api/v1/companies` — confirmed working JSON API
- **Remotive EU** — 5 job categories, filtered for EU locations
- **No Fluff Jobs** — POST API with `salaryCurrency: PLN` param (required, or it returns 400)
- **Welcome to the Jungle** — extracts from Next.js `__NEXT_DATA__` JSON blob
- **Relocate.me** — JSON patterns in HTML
- **Berlin Startup Jobs** — RSS + HTML fallback
- **GermanTechJobs** — `window.__INITIAL_STATE__` extraction
- **The Hub** (Nordics) — JSON in page + HTML fallback
- **JobFluent, Tecnoempleo, IT-Jobbank, WeAreDevelopers**
- **18 VC portfolios:** Balderton, Index Ventures, Northzone, Atomico, EarlyBird, HV Capital, a16z, Bessemer, Accel, Sequoia, Blackbird (AU), Square Peg (AU), NFX, General Catalyst, Point72, Creandum, Lakestar, Seventure

### `scrape_scaling_europe.py`
Scrapes Scaling Europe Substack for EU scaleup companies.

### `validate.py`
Deduplication engine:
- `append_batch(path)` — reads a batch CSV, deduplicates against master by company name + domain (case-insensitive), appends new rows
- `stats()` — prints breakdown by country, stage, etc.
- `export_cold_outreach()` — exports companies ready for outreach

### `visa_crossref.py`
Cross-references every company in the database against:
- **UK Skilled Worker register** — 125,767 sponsors (gov.uk CSV download)
- **Ireland Employment Permit register** — 7,880 companies
- **Netherlands IND register** — 12,787 sponsors (HTML scrape)
- **EU Blue Card** — marks "Possible" for all 28 EU member state companies
- Updates `Visa_Sponsorship` and `Visa_Sponsor_Register` fields in master CSV

### `score_shortlist.py`
Scores every company, picks top 100 (score ≥ 20):
- AI/Data keyword match in tech stack: up to +30
- Portfolio theme match (11 themes): up to +25
- Visa sponsorship confirmed: +25 / possible: +15
- EOR available: +10
- EU geography: +15 / AU+NZ: +10
- High-signal source (YC, etc.): +8
- Stage match (startup/scaleup): +5

### `enrich_shortlist.py`
For each of the top 100 companies:
1. Searches Indeed for open AI/Data Engineering roles (top 30 only, avoids rate limits)
2. Constructs LinkedIn company URL
3. Generates personalized cold email using your CV data
- Email picks best-matching project, lists actual skill overlap, uses correct visa line
- **Bug fixed this session:** "I'm about potential..." → "I'm reaching out about potential..."

### `send_outreach.py`
Full Gmail API cold email sender:
- OAuth2 via google-auth-oauthlib (credentials: `config/gmail_credentials.json`)
- `--dry-run` — preview emails without sending
- `--limit N` — send N emails (default: 20)
- `--company "Name"` — send to one specific company
- `--show-tracker` — see what's been sent
- Skips already-contacted companies, 2–5s random delay between sends
- Logs every send to `data/outreach_tracker.csv`

### `status.py`
9-section pipeline dashboard:
1. Total companies vs targets (5k min / 20k stretch)
2. Regional breakdown vs targets (25% each: EU, USA, AU/NZ, Remote)
3. Company stage breakdown
4. Visa signal counts
5. Top sectors
6. Shortlist preview (top 10)
7. Outreach status (sent / replied / reply rate)
8. Application pipeline stages
9. Recent runs + auto-generated next steps

### `tracker.py`
Application pipeline CLI:
- `list` — all applications (⚑ = follow-up due)
- `add "Company" "Role" "URL"` — add application
- `update "Company" --status "Interview" --notes "..."` — move forward
- `mark-replied "Company"` — marks outreach as Replied + auto-adds to applications at Phone Screen
- `follow-ups` — today's follow-ups
- `stats` — funnel stats (screen rate, interview rate, offer rate)
- Pipeline stages: `Shortlisted → Applied → Email Sent → Phone Screen → Interview → Technical Test → Final Round → Offer`

### `append_server.py`
Lightweight HTTP server on port 9876. Receives company data from n8n workflows via POST and appends to the master CSV. Bridge between n8n and the Python pipeline.

### `sheets_sync.py`
Syncs the master employer database to a Google Sheet for easy browsing without needing to open CSV files.

---

## Current State (as of 2026-06-10)

| Metric | Value |
|--------|-------|
| Total employers in database | **3,092** |
| Target minimum | 5,000 |
| Stretch goal | 20,000 |
| Gap to minimum | ~1,908 |
| Companies scored and shortlisted | **100** (top 100) |
| Cold emails generated | **100** |
| Cold emails sent | **0** (Gmail not yet set up) |
| Visa sponsors flagged | **299 / 3,092** |
| — UK Skilled Worker | 208 |
| — Ireland Employment Permit | 13 |
| — Netherlands IND | 5 |
| — EU Blue Card possible | 73 |

**Regional breakdown:**

| Region | Count | Target |
|--------|-------|--------|
| USA | 1,096 | 25% |
| Unknown | 1,167 | — |
| Europe | 274 | 25% |
| UK | 122 | — |
| Remote | 112 | 25% |
| Germany | 57 | — |
| Australia | 55 | — |
| Japan | 44 | — |
| Others | ~165 | — |

**Top 10 shortlisted companies (scored):**

1. Skedgo [108] — Transport Analytics
2. Holistic AI [105] — AI Governance
3. Revolut [99] — Fintech
4. Quantexa [~95] — Financial Crime AI
5. Faculty AI — GovTech AI
6. Thought Machine — Core Banking
7. Grafana Labs — Developer Tools
8. Monzo — Fintech
9. GoCardless — Payments
10. Luminance — LegalTech AI

---

## What Still Needs to be Done

### Immediate (user action required)
1. **Gmail setup** — 5 minutes on Google Console:
   - console.cloud.google.com → Create project → APIs & Services → Library → Gmail API → Enable
   - Credentials → Create OAuth client ID → Desktop app → name: `employer-discovery`
   - Download JSON → save as `config/gmail_credentials.json`
   - Run: `python3 scripts/send_outreach.py --dry-run` (one-time browser auth)

2. **Send first batch:**
   ```bash
   python3 scripts/send_outreach.py --dry-run   # preview
   python3 scripts/send_outreach.py --limit 5   # send first 5
   python3 scripts/send_outreach.py --limit 20  # daily run
   ```

### Automated (happens at 2pm daily via cron)
- `run_scrapers.py` runs automatically, adds new companies, re-scores, and re-runs visa crossref

### Future (deferred)
- **Web app UI** — FastAPI + HTML to browse companies, manage outreach, view tracker without CLI (estimated 1–2 days to build, deferred until outreach is active)
- **Grow database to 5,000+** — daily cron will get there; can also run manually anytime

---

## Key Files

```
employer-discovery/
├── scripts/
│   ├── candidate_profile.py     ← YOUR CV — edit when anything changes
│   ├── run_scrapers.py          ← Phase 1: scrape all sources
│   ├── validate.py              ← Phase 2: deduplicate + append
│   ├── visa_crossref.py         ← Phase 3: flag visa sponsors
│   ├── score_shortlist.py       ← Phase 4: score + pick top 100
│   ├── enrich_shortlist.py      ← Phase 5: open jobs + cold emails
│   ├── send_outreach.py         ← Phase 6: send via Gmail API
│   ├── status.py                ← Dashboard
│   ├── tracker.py               ← Application pipeline CLI
│   ├── scrape_usa_aunz.py       ← USA + AU/NZ scraper (new)
│   └── scrape_eu_portals.py     ← 80 EU portals + 18 VC portfolios (new)
├── data/
│   ├── master_employers.csv     ← 3,092 companies (deduped)
│   ├── cold_outreach_shortlist.csv  ← Top 100 scored
│   ├── enriched_shortlist.csv   ← Top 100 + email drafts
│   └── outreach_tracker.csv     ← (created on first send)
├── config/
│   ├── gmail_credentials.json   ← YOU NEED TO CREATE THIS
│   └── gmail_token.json         ← Auto-created after first auth
├── PIPELINE.md                  ← Full technical reference
└── SESSION_HISTORY.md           ← This file
```

---

## Daily Workflow (once Gmail is set up)

```bash
# Morning check
python3 scripts/status.py
python3 scripts/tracker.py follow-ups

# Send today's emails
python3 scripts/send_outreach.py --limit 20

# When a company replies
python3 scripts/tracker.py mark-replied "CompanyName"

# Weekly: re-scrape to add companies
python3 scripts/run_scrapers.py
```

---

## Bugs Fixed This Session

| Bug | Fix |
|-----|-----|
| `TypeError: int + NoneType` in `scrape_eu_portals.py run()` | `added = write_batch(...) or 0` |
| `jobspy` not installed | `pip3 install python-jobspy --break-system-packages` |
| Seek AU API 404 (bot blocking) | Switched to JobSpy/Indeed AU |
| EU portals returning 0 (JS-rendered) | Tested each API endpoint, rewrote to use confirmed endpoints only |
| No Fluff Jobs 400 error | Added `salaryCurrency: PLN` required param |
| Email: "I'm about potential..." | Fixed to "I'm reaching out about potential..." |
| venv tracked by git | `git rm -r --cached venv/` (files still on disk, just untracked) |
