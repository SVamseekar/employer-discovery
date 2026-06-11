# Global Employer Discovery Pipeline
> Your complete reference. If you forget what you built or where you are, start here.

---

## What This Is

A Python pipeline that finds 5,000–20,000 employers worldwide who are likely to hire you, scores them against your profile, generates personalized cold emails, and sends them via Gmail — all from your terminal.

**You are:** Marti Soura Vamseekar — AI/Data Engineer, EU Blue Card eligible, based in Hyderabad. Currently at Innosolv London (fintech, remote). MSc Data Science, University of Greenwich. Target: move to EU (Germany, Netherlands, Ireland, etc.) in an AI/Data Engineering role.

**Current state (as of last run):** ~3,068 companies in `data/master_employers.csv`. Target: 5,000 minimum, 20,000 stretch.

---

## Directory Map

```
employer-discovery/
├── scripts/
│   ├── candidate_profile.py     ← YOUR CV. Edit this when anything changes.
│   ├── run_scrapers.py          ← Phase 1: scrape all sources → batch CSVs
│   ├── validate.py              ← Phase 2: deduplicate + append to master
│   ├── visa_crossref.py         ← Phase 3: cross-reference visa registers
│   ├── score_shortlist.py       ← Phase 4: score + pick top 100 companies
│   ├── enrich_shortlist.py      ← Phase 5: find open jobs + generate emails
│   ├── send_outreach.py         ← Phase 6: send via Gmail API
│   ├── status.py                ← Dashboard: see exactly where you are
│   └── tracker.py               ← Track applications and follow-ups
├── data/
│   ├── master_employers.csv     ← All companies (deduped, 24 fields)
│   ├── cold_outreach_shortlist.csv  ← Top 100 scored companies
│   ├── enriched_shortlist.csv   ← Top 100 + open jobs + email drafts
│   ├── outreach_tracker.csv     ← Every email sent (status, reply, etc.)
│   ├── applications.csv         ← Your job application pipeline
│   └── pipeline_log.csv         ← History of every scraper run
├── config/
│   ├── gmail_credentials.json   ← OAuth client (you download this once)
│   └── gmail_token.json         ← Auto-generated after first auth
├── batches/                     ← Temporary per-scraper output files
├── PIPELINE.md                  ← This file
├── requirements.txt
└── .gitignore
```

---

## The 6-Phase Pipeline

### Phase 1 — Scrape Employers
```bash
python scripts/run_scrapers.py
```
Pulls companies from: YC API, RemoteOK, GitHub Jobs API, Remotive, EU Startups, Scaling Europe Substack, EU portals (Crunchbase, Dealroom, etc.), USA/AU/NZ job boards via JobSpy, H1B sponsor XLSX, HN Algolia.

Each scraper writes its output to `batches/`. Takes 10–30 minutes depending on rate limits.

---

### Phase 2 — Validate & Deduplicate
```bash
python scripts/validate.py
```
Reads every file in `batches/`, deduplicates against `data/master_employers.csv` (by company name + domain), and appends new rows. Prints how many were added vs skipped.

Run this after every scrape. You can also run it manually to check stats:
```bash
python scripts/validate.py stats
```

---

### Phase 3 — Visa Cross-Reference
Runs automatically as part of `run_scrapers.py` (called at the end). Can also run standalone:
```bash
python scripts/visa_crossref.py
```
Cross-references every company against:
- **UK** Skilled Worker register (141k companies, gov.uk CSV)
- **Ireland** Employment Permit register (enterprise.gov.ie Excel)
- **Netherlands** IND register (HTML scrape)
- **EU Blue Card** countries: marks "Possible" for 28 EU member states

Updates `Visa_Sponsorship` and `Visa_Sponsor_Register` fields in `master_employers.csv`.

---

### Phase 4 — Score & Shortlist
```bash
python scripts/score_shortlist.py
```
Scores every company in `master_employers.csv` against your profile. Scoring:
- AI/Data keyword match in tech stack: up to +30
- Portfolio theme match (11 themes from your plan): up to +25
- Visa sponsorship confirmed: +25 / possible: +15
- EOR available: +10
- EU geography: +15 / AU+NZ: +10
- High-signal source (YC, etc.): +8
- Stage match (startup/scaleup): +5

Top 100 companies with score ≥ 20 → saved to `data/cold_outreach_shortlist.csv`.

---

### Phase 5 — Enrich & Generate Emails
```bash
python scripts/enrich_shortlist.py
```
For each of the top 100 companies:
1. Searches Indeed for open AI/Data Engineering roles
2. Constructs LinkedIn company URL
3. Generates a personalized cold email using your CV data from `candidate_profile.py`

Output: `data/enriched_shortlist.csv` (adds `Open_Roles_Found`, `Best_Job_URL`, `LinkedIn_Company`, `Cold_Email_Draft`).

The email personalization logic:
- Picks the most thematically relevant project (AEQUITAS for transport/govtech, Masova for fintech/EU VAT, WorkforceGuard for HR analytics, etc.)
- Lists actual CV skills that match the company's tech stack
- Adds correct visa line based on company country (EU Blue Card line for EU companies, remote line for remote-only)

---

### Phase 6 — Send Cold Emails
```bash
# Preview first (no emails sent):
python scripts/send_outreach.py --dry-run

# Send 5 to test:
python scripts/send_outreach.py --limit 5

# Normal daily run:
python scripts/send_outreach.py --limit 20

# Send to one specific company:
python scripts/send_outreach.py --company "Stripe"

# See what's been sent:
python scripts/send_outreach.py --show-tracker
```

Sends from `martisoura@gmail.com` via Gmail API. Skips companies already contacted. 2–5 second random delay between sends to avoid spam flags. Logs every send to `data/outreach_tracker.csv`.

---

## Gmail One-Time Setup (5 minutes)

You only do this once. After that, the token auto-refreshes.

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project (or pick an existing one)
3. **APIs & Services → Library** → search "Gmail API" → **Enable**
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name: `employer-discovery`
5. Click **Download JSON** → save the file as `config/gmail_credentials.json`
6. Run: `python scripts/send_outreach.py --dry-run`
   - A browser tab opens for one-time Google login
   - Approve the permission ("Send email on your behalf")
   - Token saved automatically to `config/gmail_token.json`

Done. The token lasts until you revoke it. Never commit `config/` to git (it's in `.gitignore`).

---

## Your Application Tracker

```bash
# See all applications (⚑ = follow-up due):
python scripts/tracker.py list

# Filter by stage:
python scripts/tracker.py list --status Interview

# Add a new application:
python scripts/tracker.py add "Stripe" "Data Engineer" "https://stripe.com/jobs/123"

# Move it forward:
python scripts/tracker.py update "Stripe" --status "Phone Screen"
python scripts/tracker.py update "Stripe" --notes "Spoke with Sarah, technical call next week"
python scripts/tracker.py update "Stripe" --follow-up "2026-06-16"

# When a company replies to your cold email:
python scripts/tracker.py mark-replied "CompanyName"
# ^ This marks the outreach tracker as Replied AND auto-adds to applications at Phone Screen

# Today's follow-ups:
python scripts/tracker.py follow-ups

# Funnel stats (screen rate, interview rate, offer rate):
python scripts/tracker.py stats
```

Pipeline stages in order:
`Shortlisted → Applied → Email Sent → Phone Screen → Interview → Technical Test → Final Round → Offer`

---

## Dashboard — See Where You Are

```bash
python scripts/status.py
```

Shows:
1. Total companies vs plan target (5k min / 20k stretch)
2. Regional breakdown vs targets (25% each: EU, USA, AU/NZ, Remote)
3. Company stage breakdown (30% startup, 30% scaleup, etc.)
4. Visa signal counts (confirmed / possible / unknown)
5. Top sectors by count
6. Shortlist preview (top 10 scored companies)
7. Outreach status (sent / replied / reply rate)
8. Application pipeline (stage counts)
9. Recent pipeline runs
10. What to do next (auto-generated priority list)

---

## Keeping Your CV Up to Date

All CV data is in one place: `scripts/candidate_profile.py`

Edit it when:
- You change jobs
- You get a new certification
- You want to add a new project
- Your target countries change
- Your phone number or email changes

Everything else (emails, scoring, status dashboard) picks up the changes automatically — nothing else needs to be edited.

Key functions in `candidate_profile.py`:
- `get_best_project(sector, reason, tech_stack)` — picks the most relevant project for a company
- `get_skill_overlap(tech_stack)` — finds your CV skills in the company's stack
- `get_visa_line(country, remote)` — returns correct visa/relocation sentence

---

## Daily Workflow

A typical day takes about 5 minutes:

```bash
# 1. See where you are
python scripts/status.py

# 2. Send today's batch of emails
python scripts/send_outreach.py --limit 20

# 3. Check for follow-ups
python scripts/tracker.py follow-ups

# 4. Log any replies
python scripts/tracker.py mark-replied "CompanyName"
```

Once a week, re-run the full pipeline to keep adding companies:
```bash
python scripts/run_scrapers.py       # ~20 min
python scripts/score_shortlist.py
python scripts/enrich_shortlist.py   # ~10 min
```

---

## Web Portal CRM & Dashboard

Instead of managing the pipeline entirely from the command line, you can launch a local web portal:

```bash
python web/app.py
```

Then, open **[http://127.0.0.1:9800](http://127.0.0.1:9800)** in your web browser.

### Key Tab Features:
1. **Interactive Dashboard:** Tracks database growth, regional breakdown, stage percentages, and visa sponsor signals.
2. **Background Process Controller:** Trigger scrapers, visa cross-referencing, re-scoring, and shortlist enrichment directly from the UI with real-time log output streaming.
3. **Employer Explorer:** Search, filter, and sort all 3,022+ companies.
4. **Outreach Review Station:** Select shortlisted companies, check contact email, personalize/edit email drafts, and trigger Gmail sends safely with a single click (mitigating automated bounce risks).
5. **CRM Kanban Board:** Move cards through hiring stages, update notes, and see visual alerts for due follow-ups.

---


## Original Plan Targets

From your project specification:

| Target | Value |
|--------|-------|
| Total employers | 5,000 – 20,000 |
| Europe | 25% (priority region) |
| USA | 25% |
| Australia + NZ | 25% |
| Remote / Global | 25% |
| Startups | 30% |
| Scaleups | 30% |
| Mid-market | 20% |
| Enterprise | 10% |
| Hidden Champions | 10% |

**Portfolio themes scored** (from `score_shortlist.py`):
AI/Data Platform, Fintech/Insurtech, GovTech/Civic, Climate/Sustainability,
Healthcare/BioTech, Transport/Logistics, HR/WorkTech, LegalTech/RegTech,
EdTech, E-commerce/Retail AI, Developer Tools / Infrastructure

**Priority visa countries:** Germany, Netherlands, Ireland, France, Sweden, Austria, Denmark, Finland, Belgium, Switzerland — all covered by EU Blue Card.

---

## Quick Troubleshooting

**`validate.py` can't find master_employers.csv**
→ Run from any directory, it uses absolute paths. If the file doesn't exist yet: `python scripts/import_h1b.py` to create it from the H1B XLSX.

**Gmail auth fails / token expired**
→ Delete `config/gmail_token.json` and run `--dry-run` again to re-authenticate.

**enrich_shortlist.py is slow**
→ It searches Indeed for the top 30 companies (with 1s delays). This is expected. It skips JobSpy for positions 31–100.

**Score shortlist is empty**
→ Check that `master_employers.csv` exists and has rows. Run `python scripts/validate.py stats` to confirm.

**`send_outreach.py` says "enriched_shortlist.csv not found"**
→ Run `python scripts/enrich_shortlist.py` first.

---

## What Was Built (Session Summary)

These files were created or improved in the last session:

| File | What changed |
|------|-------------|
| `scripts/candidate_profile.py` | **New** — all CV data; smart project/skill/visa matching; `get_language_line()` added |
| `scripts/enrich_shortlist.py` | Updated to use `candidate_profile.py` + language_req support |
| `scripts/send_outreach.py` | **New** — full Gmail API cold email sender with language_req support |
| `scripts/status.py` | **New** — pipeline dashboard with progress bars and auto next-steps |
| `scripts/tracker.py` | **New** — application tracker CLI with funnel stats and follow-up alerts |
| `scripts/validate.py` | Bug fix: absolute path + `return added` in `append_batch` |
| `scripts/run_scrapers.py` | Bug fix: Remotive logo URL fix |
| `scripts/scrape_directories.py` | **Expanded** — USA: 15 → 44 cities; EU: 5 → 66 cities across 20+ countries |
| `requirements.txt` | Updated with all dependencies including Google API libs |
| `.gitignore` | **New** — excludes venv, all CSVs, Gmail tokens, __pycache__ |
