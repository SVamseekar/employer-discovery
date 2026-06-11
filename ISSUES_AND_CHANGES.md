# Issues, Opinions & Changes Log
> Single reference for everything raised, decided, and built across all sessions.
> Read this before touching any file. Keep it updated as the project evolves.

---

## Part 1 — Every Issue You Raised (+ My Honest Opinion)

---

### Issue 1: EU coverage was too narrow
**You said:** "By europe I want more regions to be in the automation, more tier 2/3 regions."

**What was wrong:** `scrape_eu_cities()` in `scrape_directories.py` only covered 5 cities:
Berlin, Amsterdam, Stockholm, Dublin, Lisbon. That's barely any of the EU tech ecosystem.

**Fix applied:** Expanded to 68 cities across 26 countries, covering every meaningful tier.
Germany alone went from 1 to 9 cities (Berlin, Munich, Hamburg, Frankfurt, Cologne, Stuttgart,
Leipzig, Düsseldorf, Dresden). Added France (6 cities), Spain (5), Italy (4), Netherlands (4),
Poland (4), Czech Republic, Austria, Sweden, Denmark, Finland, Belgium, Switzerland, Norway,
Ireland, Portugal, Romania, Baltics, Balkans, Luxembourg.

**My opinion:** This should've been the default from the start. Europe has massive hidden
champion ecosystems outside capital cities — Leipzig has a strong ML scene (Fraunhofer),
Toulouse is where Airbus and aerospace-adjacent AI lives, Cluj-Napoca is Romania's
underrated engineering hub, Tampere in Finland has solid industrial AI. You were missing all of them.

---

### Issue 2: USA coverage was too shallow
**You said:** "In usa more companies should come out."

**What was wrong:** `scrape_usa_tier2()` in `scrape_directories.py` had 15 cities.
`scrape_usa_jobspy()` in `scrape_usa_aunz.py` had 7 (tier 1) + 15 (tier 2/3) = 22 total.

**Fix applied:**
- `scrape_directories.py` → 15 → **54 cities** (added tier 2: Charlotte, San Jose, Bellevue,
  Sacramento, Tampa, Orlando, Kansas City, Cincinnati, Columbus, Indianapolis, Cleveland;
  tier 3: Provo, Boise, Madison, Milwaukee, Louisville, Richmond, Oklahoma City, Tulsa, Omaha,
  Des Moines, San Antonio, Jacksonville, Huntsville, New Orleans, Hartford, Providence, Buffalo,
  Rochester, Las Vegas, Tucson, Colorado Springs, Spokane, Albuquerque, Memphis, Fargo,
  Sioux Falls, Honolulu)
- `scrape_usa_aunz.py` → tier2 list expanded from 15 to 41 cities

**My opinion:** Huntsville AL (DoD tech), Boise ID (Micron semiconductor ecosystem), Provo UT
(strong startup base near BYU, low competition), Fargo ND (Microsoft campus) — these are exactly
the "hidden champion" cities your plan targets. You'd find companies there that aren't on anyone
else's radar.

---

### Issue 3: Language learning — add acknowledgment in emails
**You said:** "Regarding language thing I want to add that for that particular lang, I want to
say I am learning and I'm a beginner."

**What was wrong:** Companies with German/Dutch/Japanese requirements were getting through to the
shortlist and receiving emails with zero acknowledgment of the language mismatch. That's dishonest
and would get you screened out immediately if they noticed.

**Fix applied:** Added `get_language_line()` in `candidate_profile.py`. Added German, Dutch,
Japanese as "beginner" in your language dict. Updated `send_outreach.py` and `enrich_shortlist.py`
to pass `language_req` and insert the line.

Example output for a German-requirement company:
> "On the language front — I'm currently learning German and am at beginner level.
> I'm actively studying and committed to reaching professional proficiency.
> In the meantime I'm fully productive in English."

**My opinion:** This is the right call. Being transparent about language level is actually a
positive signal — it shows self-awareness and proactiveness. What you should NOT do is silently
send a "fluent" signal when you're not. The line as written hits the right tone.

**One thing I'd add in future:** Consider adding a "Language_Exclude" flag for companies that
explicitly require C1/C2 German (i.e., not remote-friendly and no English fallback). Those
companies won't respond regardless of how honest you are. The data is already captured in
`Language_Requirement` — a score penalty for confirmed non-English requirements would help.

---

### Issue 4: Are all filters implemented?
**You asked:** "Are all my filters implemented?"

**Audit result — filters that EXIST but are NOT used in scoring/email logic:**

| Field | Stored? | Used in scoring? | Used in emails? | Used to filter? |
|-------|---------|-----------------|-----------------|-----------------|
| `Language_Requirement` | ✓ | ✗ | ✓ (after fix) | ✗ |
| `Region_Eligibility` | ✓ | ✗ | ✗ | ✗ |
| `Target_Roles` | ✓ | ✗ | ✗ | ✗ |
| `Company_Scale` | ✓ | ✗ | ✗ | ✗ |
| `Portfolio_Theme_Match` | ✓ | ✗ | ✗ | ✗ |
| `Visa_Sponsorship` | ✓ | ✓ (+25/+15) | ✓ (visa line) | ✗ |
| `Company_Stage` | ✓ | +5 (YC only) | ✗ | ✗ |
| `Remote` | ✓ | ✗ | ✓ (visa line) | ✗ |
| `Hiring_Confidence` | ✓ | ✗ | ✗ | ✗ |

**What this means:** The scoring is currently doing about 40% of what it should. The biggest
gaps:
- `Region_Eligibility` is never read — companies in regions you explicitly can't work in still
  score the same as EU companies
- `Target_Roles` is never matched — a company hiring only iOS developers scores the same as one
  hiring data engineers
- `Company_Stage` only boosts YC companies, not startups/scaleups in general

**My recommendation for a future session:** Add these score adjustments to `score_shortlist.py`:
- `Target_Roles` contains "data" or "AI" or "engineer" → +15
- `Region_Eligibility` = "Eligible" → +10
- `Company_Stage` in ("Startup", "Scaleup") → +8
- `Language_Requirement` is non-English → -10 (unless "Learning" → 0)
These are straightforward dict lookups, low risk to add.

---

### Issue 5: Tiering for ALL regions (EU, India, AU, NZ, Japan)
**You said:** "Do the tiering in EU India AU NZ Japan as well please, so maintain those rules for
every region I gave."

**Status before this session:**
- EU: 5 cities (no tiering) — NOW FIXED (68 cities, 26 countries)
- USA: 22 cities (loose tiering) — NOW FIXED (54+ cities)
- India: 1 search ("India" as a whole location) — NOW FIXED
- AU: 6 cities (no tier 3) — NOW FIXED
- NZ: 3 cities (no tier 3) — NOW FIXED
- Japan: NO SCRAPER AT ALL — NOW FIXED

**India tier breakdown (19 cities):**
- Tier 1: Bangalore, Mumbai, Delhi, Hyderabad, Chennai
- Tier 2: Pune, Kolkata, Ahmedabad, Noida, Gurgaon, Coimbatore
- Tier 3: Jaipur, Kochi, Indore, Chandigarh, Bhubaneswar, Nagpur, Mysore, Lucknow

**Australia tier breakdown (12 cities):**
- Tier 1: Sydney, Melbourne
- Tier 2: Brisbane, Perth, Adelaide, Canberra
- Tier 3: Gold Coast, Newcastle, Wollongong, Hobart, Darwin, Sunshine Coast

**New Zealand tier breakdown (6 cities):**
- Tier 1: Auckland
- Tier 2: Wellington, Christchurch
- Tier 3: Hamilton, Dunedin, Tauranga

**Japan tier breakdown (11 cities):**
- Tier 1: Tokyo, Osaka
- Tier 2: Yokohama, Nagoya, Fukuoka, Sapporo, Kyoto
- Tier 3: Sendai, Hiroshima, Kobe, Kawasaki

**My opinion on India:** This was a critical gap. You're currently based in Hyderabad — Indian
companies are your most accessible market right now. Noida/Gurgaon cover the Delhi NCR corridor
where half of India's enterprise tech hiring happens. Coimbatore is underrated — strong
mid-market engineering firms (Zoho, KGISL, etc.). Tier 3 cities matter because GovTech and
Industrial AI companies (ISRO vendors, DRDO-adjacent firms, PSU software arms) tend to be
headquartered there, not in Bangalore.

**My opinion on Japan:** Japan is genuinely tricky. The tech job market is highly relationship-
driven. However, Tokyo has a real English-friendly tech ecosystem: Mercari, Rakuten (some teams),
Sony's AI research labs, SmartNews, Preferred Networks, PayPay, LINE, AWS Japan, Google Japan.
These companies are actively recruiting internationally. The `Language_Requirement` is set to
"Japanese (Learning)" for all Japan rows, so the email pipeline will automatically add the honest
language acknowledgment. Do NOT send to Japanese companies that don't list English as an option —
those will be filtered out naturally by score if you add the language penalty.

---

### Issue 6: "I need to make a list of 1000s of companies"
**You said:** "I need to make a list of 1000s of companies... if we see them then there would be
more companies."

**Current state:** ~3,068 companies in `master_employers.csv`.
**Target:** 5,000 minimum, 20,000 stretch.

**Projected output after all region expansions (per full run):**
- EU JobSpy (68 cities × 30 results): ~2,040 raw hits → ~500-800 new after dedup
- USA JobSpy (54 cities × 40 results): ~2,160 raw hits → ~400-700 new after dedup
- India (19 cities × 40 results): ~760 raw hits → ~200-350 new after dedup
- Japan (11 cities × 25 × 2 terms): ~550 raw hits → ~100-200 new after dedup
- AU/NZ JobSpy (18 cities × 50 results): ~900 raw hits → ~150-300 new after dedup
- Seek, Adzuna, Jora, CareerOne, Built In, Dice: additional ~500-1,000 new

**Conservative estimate:** 5,000+ companies after 2 full runs. 10,000+ after 4-5 runs.
This is achievable. The bottleneck is IndeedJobSpy rate limits, not company availability.

---

## Part 2 — My Opinions / Things You Didn't Ask But Should Know

---

### Opinion A: Your shortlist cap of 100 is too small

`score_shortlist.py` saves only the top 100. With 5,000+ companies in master, that's a 2%
capture rate. Many genuinely good companies will be ranked #101-#500 and never see an email.

**Recommendation:** Increase to 500. The scoring already works — just change the limit.
In `score_shortlist.py`, find `[:100]` and change to `[:500]`.

---

### Opinion B: India is your immediate market — treat it differently

Indian companies don't need visa sponsorship complexity. The email template should not say
"EU Blue Card eligible" to an Indian company — it's irrelevant and sounds off.

`get_visa_line()` in `candidate_profile.py` currently defaults to the EU Blue Card line for any
non-EU, non-remote company. For Indian companies, the right line is:
> "I'm currently based in Hyderabad and available for both in-person and remote work."

**Fix needed:** Add India to `get_visa_line()`:
```python
if any(c in combined for c in ["india", "bangalore", "hyderabad", "mumbai", "delhi"]):
    return "I'm based in Hyderabad and available immediately for in-office or hybrid roles."
```

---

### Opinion C: The "hidden champion" target has no dedicated scraper

Your plan says 10% hidden champions. None of the scrapers specifically target them.

Hidden champions = mid-sized B2B companies, often not venture-backed, rarely on job boards,
but have stable engineering teams and hire internationally. Examples: KION Group, Wacker Chemie,
Herrenknecht (all German), or Cochlear/NEXTDC (Australia).

**Best proxy sources** (worth adding in a future session):
- Germany: `mittelstand-digital.de` company list
- Netherlands: FD Gazellen (fast-growing Dutch companies)
- EU: eurochambers.eu member directories
- AU: BRW Fast 100 list
- India: Nasscom Emerge 50 list

---

### Opinion D: Follow-up emails are missing and matter more than first emails

The pipeline sends one email and moves on. In reality, 70-80% of cold email replies come from
follow-ups 5-10 days after the first email. Without this, you're leaving most of your reply rate
on the table.

**What's needed:** A `scripts/followup.py` that:
- Reads `outreach_tracker.csv`
- Finds companies where Status = "Sent" and Sent_At is 5-7 days ago
- Generates a shorter follow-up ("I wanted to follow up on my email from last week...")
- Sends via Gmail API (same flow as `send_outreach.py`)

This is the single highest-ROI feature not yet built.

---

### Opinion E: No deduplication by country distribution

Your targets say 25% each for EU, USA, AU+NZ, Remote. The deduplication in `validate.py`
deduplicates by name+domain but doesn't enforce regional balance. If all 3,068 current companies
are USA-heavy (they probably are, given H1B import + YC + HN), your scoring will naturally
surface mostly USA companies.

`score_shortlist.py` adds +15 for EU and +10 for AU/NZ, which partially corrects this, but it's
not enough to hit 25% non-USA if the raw population is 70% USA.

**Recommendation:** Add a regional quota to `score_shortlist.py` — after scoring, split the
shortlist into 4 buckets and take the top N from each. This guarantees geographic diversity.

---

## Part 3 — Every File Changed and Why

---

| File | What changed | Why |
|------|-------------|-----|
| `scripts/candidate_profile.py` | Added `languages` dict with German/Dutch/Japanese as beginner. Added `get_language_line()` function. | You asked for honest language acknowledgment in emails. This is the single source of truth for all CV data. |
| `scripts/send_outreach.py` | Updated import to include `get_language_line`. Updated `build_body()` signature to accept `language_req`. Added `lang_block` insertion between visa line and closing question. | Without this, emails to German/Dutch/Japanese-requirement companies had no language mention — dishonest and likely to get you filtered. |
| `scripts/enrich_shortlist.py` | Updated import. Updated `generate_email()` to accept and use `language_req`. Updated call site to pass `row.get("Language_Requirement", "")`. | Same reason as above — enrichment phase generates email drafts, they need the same language logic. |
| `scripts/scrape_directories.py` | EU cities: 5 → 68 across 26 countries. Australia/NZ in `scrape_australia_nz()`: 6 → 18 cities (added tier 3). USA in `scrape_usa_tier2()`: 15 → 54 cities (added tier 2 + tier 3). | Your original plan specified 40% Tier 2 + 30% Tier 3 coverage. The old setup was doing roughly 20% tier 2, 0% tier 3. |
| `scripts/scrape_usa_aunz.py` | `scrape_usa_jobspy()` tier 2 list expanded from 15 to 41 cities. `scrape_aunz_jobspy()` expanded from 9 to 18 AU/NZ cities (added tier 3 for both countries). | This is the second USA scraper (complements scrape_directories.py). Both needed expanding for consistent coverage. |
| `scripts/run_scrapers.py` | `scrape_india()` rewritten from single "India" location to 19 city-by-city calls across T1/T2/T3. Added new `scrape_japan()` function with 11 cities × 2 search terms. Added `total += scrape_japan()` in the run block. | India had zero tiered coverage. Japan had no scraper at all. Both are in your target regions. |
| `PIPELINE.md` | Updated file change table to reflect new city counts. | Keeping the reference doc accurate. |
| `ISSUES_AND_CHANGES.md` | New file — this document. | You asked for a single doc covering all issues, opinions, and changes. |

---

## Part 4 — What's Still Pending (Next Session Priorities)

In rough priority order:

1. **Fix `get_visa_line()` for India** — currently sends EU Blue Card line to Indian companies,
   which is wrong. 5-minute fix in `candidate_profile.py`. (HIGH PRIORITY — affects every
   Indian email)

2. **Increase shortlist from 100 → 500** — change `[:100]` to `[:500]` in `score_shortlist.py`.
   (10-second fix, high impact)

3. **Add score adjustments for unused filters** — `Target_Roles`, `Region_Eligibility`,
   `Company_Stage` in `score_shortlist.py`. (1-2 hours, significant quality improvement)

4. **Add language score penalty** — non-English requirement (non-"Learning") → -10 in scoring.
   Companies that require C1 German and have no English option shouldn't be in the shortlist.

5. **Build `followup.py`** — single most impactful missing feature. Without follow-ups, you're
   operating at maybe 25% of possible reply rate.

6. **Regional quota in shortlist** — enforce 25% each bucket in `score_shortlist.py` to match
   your original plan distribution.

7. **Increase `results_wanted` for EU cities** — currently 30 per city. Could safely go to 50.
   That's +1,200 more raw EU hits per run.

8. **Add hidden champion scrapers** — Mittelstand directories (DE), Nasscom Emerge 50 (IN),
   BRW Fast 100 (AU), FD Gazellen (NL). None of these are in the pipeline yet.

---

## Quick Reference: City Counts by Region (After All Fixes)

| Region | Before | After | Countries/States |
|--------|--------|-------|-----------------|
| EU | 5 | 68 | 26 countries |
| USA | 22 | 54+ | 35+ states |
| India | 1 (whole country) | 19 | 10 states |
| Australia | 6 | 12 | All major states |
| New Zealand | 3 | 6 | North + South Island |
| Japan | 0 | 11 | 8 prefectures |
| **Total** | **37** | **170+** | |

---

## Part 5 — Source Strategy (Full Map)

6 scraper files, 3 enrichment files, ~40+ distinct sources. Here is exactly what runs,
what it contributes, and where the gaps are.

---

### Layer 1 — Startup / Tech Directories
Company names directly — not job postings. Best for hidden champions, startups, VC-backed companies.

| Source | File | What it gives | Region |
|--------|------|--------------|--------|
| YC API | `run_scrapers.py` | All YC-backed companies (400+ per batch) | Global |
| GitHub API | `run_scrapers.py` | Orgs with active RAG/dbt/LLM repos | Global |
| HN Who is Hiring | `scrape_directories.py` + `scrape_usa_aunz.py` | Companies actively posting to HN | Global/USA |
| Scaling Europe Substack | `scrape_scaling_europe.py` | EU startups from newsletter | EU |
| Built In (13 city subdomains) | `scrape_usa_aunz.py` | Curated USA tech company database | USA |
| F6S Startups | `scrape_usa_aunz.py` | USA startup registry | USA |
| ProductHunt | `scrape_usa_aunz.py` | Active SaaS/tech products | USA/Global |
| StartupAus, Stone & Chalk, AWS Startups AU, GovHack | `scrape_usa_aunz.py` | AU tech company lists | Australia |
| Papers With Code | `scrape_directories.py` | Research-backed AI/ML organizations | Global |
| H1B Sponsor XLSX | `import_h1b.py` | Confirmed US visa sponsors (141k records) | USA |

---

### Layer 2 — Job Boards (City-by-City)
Finds companies by seeing who is actively posting jobs. Highest volume source.

| Source | File | Cities | Region |
|--------|------|--------|--------|
| Indeed/LinkedIn via JobSpy | `scrape_directories.py` | 68 EU cities, 26 countries | EU |
| Indeed/LinkedIn via JobSpy | `run_scrapers.py` | 19 India cities (T1/T2/T3) | India |
| Indeed via JobSpy | `run_scrapers.py` | 11 Japan cities (T1/T2/T3) | Japan |
| Indeed via JobSpy | `scrape_usa_aunz.py` | 7 T1 + 41 T2/3 USA cities | USA |
| Indeed via JobSpy | `scrape_directories.py` | 54 USA cities (T1/T2/T3) | USA |
| Indeed/LinkedIn via JobSpy | `scrape_usa_aunz.py` + `scrape_directories.py` | 12 AU + 6 NZ cities (all tiers) | AU/NZ |
| Seek AU | `scrape_usa_aunz.py` | 6 AU cities × 4 search terms | Australia |
| Seek NZ | `scrape_usa_aunz.py` | 3 NZ cities × 3 search terms | New Zealand |
| Adzuna AU + NZ | `scrape_usa_aunz.py` | National + city level | AU/NZ |
| Jora AU | `scrape_usa_aunz.py` | 5 AU cities | Australia |
| CareerOne AU | `scrape_usa_aunz.py` | National | Australia |
| Dice.com | `scrape_usa_aunz.py` | National USA, tech-specific | USA |

---

### Layer 3 — Remote / Global Job Boards
Companies explicitly open to distributed hiring — your strongest play as a remote candidate.

| Source | File | Notes |
|--------|------|-------|
| RemoteOK API | `run_scrapers.py` + `scrape_usa_aunz.py` | Global remote; strong EU+USA representation |
| Remotive API | `run_scrapers.py` | Filtered for EU, then general remote |
| EU Remote Jobs, WeAreDevelopers, Honeypot | `scrape_eu_portals.py` | EU-remote specific |
| Relocate.me | `scrape_eu_portals.py` | Companies that actively help with relocation — directly relevant |

---

### Layer 4 — EU Specialist Portals + VC Portfolios
Highest-quality EU signal. VC-backed companies or on country-specific tech job boards.

| Source | File | Notes |
|--------|------|-------|
| Landing.jobs | `scrape_eu_portals.py` | Portugal/Spain/EU tech jobs |
| No Fluff Jobs | `scrape_eu_portals.py` | Poland's top tech job board |
| Welcome to the Jungle | `scrape_eu_portals.py` | France's top tech employer brand platform |
| Berlin Startup Jobs | `scrape_eu_portals.py` | Germany startup-specific |
| GermanTechJobs | `scrape_eu_portals.py` | Germany tech roles in English |
| DutchTechJobs | `scrape_eu_portals.py` | Netherlands tech roles in English |
| SwissDevJobs | `scrape_eu_portals.py` | Switzerland tech |
| IT-Jobbank DK | `scrape_eu_portals.py` | Denmark IT jobs |
| JobFluent, Tecnoempleo | `scrape_eu_portals.py` | Spain tech boards |
| Bulldogjob, Demando | `scrape_eu_portals.py` | Poland/CEE developer jobs |
| Honeypot | `scrape_eu_portals.py` | Developer-first job platform (EU) |
| **Balderton, Index, Northzone, Atomico, EarlyBird, HV Capital** | `scrape_eu_portals.py` | Top EU VC portfolios |
| **a16z, Bessemer, Accel, Sequoia** | `scrape_eu_portals.py` | US VCs with EU portfolio companies |
| **Blackbird, Square Peg** | `scrape_eu_portals.py` | AU/NZ focused VCs |

---

### Layer 5 — Visa Signal Enrichment (Post-scrape, not discovery)
These don't add new companies — they cross-reference existing ones to confirm or flag sponsorship.

| Source | File | Covers |
|--------|------|--------|
| UK Skilled Worker register | `visa_crossref.py` | 141k confirmed UK sponsors |
| Ireland Employment Permit | `visa_crossref.py` | Irish sponsors |
| Netherlands IND | `visa_crossref.py` | Dutch sponsors |
| EU Blue Card signal | `visa_crossref.py` | 28 EU member states (flags "Possible") |

---

### How It All Runs (Execution Order)

```
python scripts/run_scrapers.py
  │
  ├── YC API, RemoteOK, GitHub, Remotive, EU Startups
  ├── India (19 cities × 40 results via JobSpy)
  ├── Japan (11 cities × 2 terms × 25 results via JobSpy)
  │
  ├── scrape_scaling_europe.py   → EU newsletter (Scaling Europe Substack)
  │
  ├── scrape_directories.py      → HN Hiring
  │                              → AU/NZ (18 cities via JobSpy)
  │                              → USA (54 cities via JobSpy)
  │                              → EU (68 cities via JobSpy)
  │                              → Papers With Code AI orgs
  │
  ├── scrape_usa_aunz.py         → USA (48 cities via JobSpy)
  │                              → Dice.com, Built In (13 cities)
  │                              → F6S, ProductHunt
  │                              → RemoteOK USA, HN USA
  │                              → Seek AU (6 cities), Seek NZ (3 cities)
  │                              → Adzuna AU, Adzuna NZ
  │                              → Jora AU, CareerOne AU
  │                              → AU/NZ JobSpy (18 cities)
  │                              → StartupAus, Stone & Chalk, GovHack
  │
  ├── scrape_eu_portals.py       → 18 EU specialist job boards
  │                              → 12 VC portfolios (EU + AU/NZ)
  │
  ├── visa_crossref.py           → enriches Visa_Sponsorship field
  ├── score_shortlist.py         → top 100 (pending: raise to 500)
  └── enrich_shortlist.py        → open jobs + cold email drafts
```

---

### Gaps — What's Missing and Whether It Matters

| Missing Source | Region | Priority | Why |
|---------------|--------|----------|-----|
| **Naukri.com** | India | 🔴 HIGH | India's #1 job board — Indeed India has ~20% of what Naukri has for tech roles. Without this, India coverage is significantly underrepresented despite 19 cities. |
| **LinkedIn India company search** | India | 🔴 HIGH | Many Indian mid-market companies (not on job boards) are discoverable only via LinkedIn company pages. |
| **Wantedly** | Japan | 🟡 MEDIUM | Japan's startup-friendly job platform, many English-listed roles. Better than Indeed Japan for startups. |
| **Gaijin Pot Jobs** | Japan | 🟡 MEDIUM | Specifically English-friendly Japan jobs — very relevant to your situation. |
| **Wellfound / Angel.co** | Global | 🟡 MEDIUM | Startup-heavy, good for Series A/B companies. Needs a Python scraper since no public API. |
| **Trade Me Jobs** | New Zealand | 🟡 MEDIUM | NZ's second-largest job board after Seek — not currently scraped. |
| **Mittelstand directories** (mittelstand-digital.de) | Germany | 🟡 MEDIUM | Germany's hidden champions are NOT on job boards — this is the only way to reach them. |
| **Nasscom Emerge 50** | India | 🟡 MEDIUM | India's curated list of high-growth tech companies — maps directly to hidden champion target. |
| **BRW Fast 100** | Australia | 🟢 LOW | AU fast-growing companies list — good for hidden champions. |
| **FD Gazellen** | Netherlands | 🟢 LOW | NL's fast-growing company list — similar to Mittelstand but Dutch. |
| **GovTech Singapore, InvestHK** | Asia | 🟢 LOW | Only relevant if expanding beyond India/Japan. |
| **Glassdoor** | Global | ⛔ SKIP | Blocked / requires auth — not practically scrapable. |

**Single highest-impact missing source: Naukri.com.** You are based in Hyderabad. India is your
immediate market. Naukri has 10× the India tech job data that Indeed has. Adding a Naukri scraper
would likely double your India company count in one run.

---

---

## Part 6 — Scoring System (Exactly How Companies Are Ranked)

Every company in `master_employers.csv` is scored by `score_shortlist.py`.
Top 100 with score ≥ 20 go to the shortlist. (Target: raise to 500 — see Pending #2.)

### Score Breakdown

| Signal | Max Points | How It's Calculated |
|--------|-----------|---------------------|
| AI/Data keyword match | +30 | Sector + Tech_Stack checked against 20 keywords (ai, ml, llm, rag, dbt, databricks, spark, kafka, pipeline, cloud, geospatial, etc.). +6 per keyword, capped at 30. |
| Portfolio theme match | +25 | 11 themes checked against all text fields. +8 per matched theme, capped at 25. |
| Visa — confirmed sponsor | +25 | Visa_Sponsorship = "Yes" OR register = UK/Ireland/Netherlands confirmed |
| Visa — EU Blue Card country | +15 | EU Blue Card register OR Visa_Sponsorship = "Possible" |
| Visa — other register signal | +8 | Any other non-empty, non-unknown register value |
| EU geography | +15 | Country or Hiring_Geography contains any EU country |
| EOR available | +10 | EOR field = "Yes" |
| Australia / New Zealand | +10 | Country or Hiring_Geography contains "australia" or "new zealand" |
| Remote | +8 | Remote = "Yes" (only if not EU — EU already gets +15) |
| High-signal source category | +8 | Category is: YC, Remote-first, EU Startup, EU Remote, EU Tech, GitHub Signal, Remotive, India Tech, HN Hiring, AU/NZ Tech |
| Startup / growth stage | +5 | Company_Stage contains: startup, series a/b/c, scale, growth, scaleup |
| Hiring confidence — high | +5 | Hiring_Confidence = "High" |
| Hiring confidence — medium | +2 | Hiring_Confidence = "Medium" |
| YC backed | +5 | Employer_Category or Source contains "yc" |

**Maximum possible score: ~118 points**
**Minimum to make shortlist: 20 points**

### The 11 Portfolio Themes (and Their Keywords)

These are the themes from YOUR projects that score_shortlist.py checks for:

| Theme | Trigger Keywords |
|-------|-----------------|
| AI Assurance | ai assurance, ai safety, ai audit, model governance |
| AI Governance | ai governance, ai policy, responsible ai, ai regulation |
| EU Policy | eu policy, eu regulation, gdpr, ai act, european |
| Workforce Analytics | workforce, hr analytics, people analytics, talent analytics |
| Transport Analytics | transport, mobility, logistics, fleet, transit, rail |
| Smart Cities | smart city, smart cities, urban, city data, municipal |
| Geospatial | geospatial, gis, mapping, location, spatial, satellite |
| Fintech Infrastructure | fintech, payments, banking, financial infrastructure |
| Compliance Systems | compliance, regtech, regulatory, aml, kyc, audit |
| Public Sector Analytics | govtech, public sector, government, civic |
| Enterprise Data Platforms | data platform, data warehouse, lakehouse, enterprise data |

**Missing portfolio themes (not yet in scoring):**
- HealthTech / BioTech (you have Python/ML skills applicable here)
- ClimateTech / GreenTech (strong EU alignment)
- LegalTech (your Masova project has compliance overlap)
- Industrial AI / Manufacturing AI

---

## Part 7 — Original Plan Targets

These are the distribution targets from your original project spec. The pipeline doesn't yet
enforce these — it scores and filters but doesn't quota-balance. Adding regional + stage quotas
to `score_shortlist.py` is Pending #6.

### Company Count Target
| Target | Value |
|--------|-------|
| Minimum | 5,000 companies |
| Stretch | 20,000 companies |
| Current | ~3,068 companies |

### Geographic Distribution Target (25% each)
| Region | Target | Current estimate |
|--------|--------|-----------------|
| Europe | 25% | ~20% (improving with 68-city EU scrape) |
| USA | 25% | ~40% (over-represented due to H1B + YC + HN) |
| Australia + NZ | 25% | ~10% (improving with tier 3 expansion) |
| Remote / Global | 25% | ~15% |

### Company Stage Distribution Target
| Stage | Target | Notes |
|-------|--------|-------|
| Startup | 30% | Pre-seed to Series B |
| Scaleup | 30% | Series C+ to ~500 employees |
| Mid-market | 20% | 500–5,000 employees |
| Enterprise | 10% | 5,000+ employees |
| Hidden Champion | 10% | B2B, not VC-backed, strong engineering |

### Target Sectors (from original plan)
AI Infrastructure · GovTech · RegTech · FinTech · HealthTech · ClimateTech ·
Transport Analytics · Smart Cities · Geospatial · Cybersecurity · Industrial AI ·
LegalTech · Public Sector Analytics · Workforce Analytics · EdTech ·
E-commerce/Retail AI · Developer Tools / Infrastructure

### Target City Mix (across all regions)
| Tier | Target % | Current status |
|------|----------|---------------|
| Tier 1 (capitals + mega hubs) | 30% | Over-represented (was the default) |
| Tier 2 (secondary hubs) | 40% | Now properly covered (expansions done) |
| Tier 3 (rising ecosystems) | 30% | Now covered for all regions |

---

## Part 8 — Visa & Language Field Reference

### Visa_Sponsorship Field Values
Set by `visa_crossref.py` after scraping.

| Value | Meaning | Score impact |
|-------|---------|-------------|
| `Yes` | Found on UK/Ireland/Netherlands confirmed register | +25 |
| `Possible` | Company is in an EU Blue Card country (28 countries) | +15 |
| `No` | Actively checked and not found on any register | 0 |
| `Unknown` | Not yet cross-referenced | 0 |

### Visa_Sponsor_Register Field Values
| Value | Meaning |
|-------|---------|
| `UK Skilled Worker` | On UK gov.uk Skilled Worker register |
| `Ireland Employment Permit` | On enterprise.gov.ie register |
| `Netherlands IND` | On Dutch IND register |
| `EU Blue Card - [Country]` | In an EU Blue Card eligible country |
| `Not Found` | Checked, not on any register |
| `Unknown` | Not yet checked |

### EU Blue Card Countries (28 — all flagged "Possible" if not on a specific register)
Germany · France · Netherlands · Belgium · Austria · Sweden · Denmark · Finland ·
Spain · Portugal · Poland · Czech Republic · Hungary · Romania · Bulgaria · Croatia ·
Slovakia · Slovenia · Estonia · Latvia · Lithuania · Luxembourg · Malta · Cyprus ·
Greece · Italy · Ireland · (+ Norway/Switzerland as associates)

### Language_Requirement Field Values
Set at scrape time based on job posting language or company country.

| Value | Meaning | Email action |
|-------|---------|-------------|
| `English` | English required or English-first market | No language line added |
| `None` | Not specified / remote / global | No language line added |
| `Unknown` | Could not determine | No language line added |
| `German (Learning)` | German required, you are learning | Adds honest learning line |
| `Dutch (Learning)` | Dutch required, you are learning | Adds honest learning line |
| `Japanese (Learning)` | Japanese required, you are learning | Adds honest learning line |

**All Japan rows are tagged `Japanese (Learning)` automatically at scrape time.**
**Future:** Add `-10` score penalty for `(Learning)` languages to deprioritize them unless
you specifically want to target them.

---

## Part 9 — The Accessibility Problem & Layer 0 Fix

### The Real Problem With Job Board Scrapers

Claude Code (and any automated tool) faces systematic blocking when hitting job boards:

| Source | Block Type | Impact |
|--------|-----------|--------|
| Indeed / JobSpy | Cloudflare, SIGALRM timeout, rate limits | Partial data — some cities time out |
| LinkedIn | Anti-bot detection, auth walls | JobSpy LinkedIn module unreliable |
| Naukri.com | Bot detection + JS rendering | Near zero data returned |
| StepStone | Cloudflare | Returns nothing |
| Dice.com | API endpoint changed, HTML fragile | ~0 actual company names |
| Built In | JavaScript-rendered, no SSR content | Regex returns empty |
| Glassdoor | Heavy bot detection | Blocked |
| Wantedly | Requires login for full listings | Blocked |

**The root cause:** The pipeline was 80% dependent on job board scraping (fragile layer)
and 20% on static/API sources (reliable layer). When job boards block, the pipeline returns
thin results and you can't tell what succeeded vs. what silently failed.

### The Fix: Layer 0 Architecture

**Pipeline layers, most reliable → least reliable:**

```
Layer 0: static_companies.py     → 211 hardcoded FAANG/MNCs [NEVER FAILS]
Layer 1: API sources              → YC API, RemoteOK API, GitHub API [RELIABLE]
Layer 2: VC portfolios + HTML     → Portfolio pages, Scaling Europe [RELIABLE]
Layer 3: JobSpy city-by-city      → Indeed per city [FRAGILE — log failures]
Layer 4: Direct portal scrapers   → Dice, Built In, etc. [OFTEN BLOCKED]
```

**Layer 0 is the rock.** Even if layers 2-4 all fail completely, you still get 211
high-quality companies every single run. These are FAANG, EU MNCs, India top employers,
Japan big tech, AU/NZ leaders — all hardcoded with full metadata.

### What's in static_companies.py (211 companies)

| Region | Count | Notable names |
|--------|-------|--------------|
| USA — Big Tech / FAANG | 35 | Google, Meta, Amazon, Microsoft, Apple, Netflix, Nvidia, Snowflake, Databricks |
| USA — AI/Data Specialists | 30 | OpenAI, Anthropic, Cohere, dbt Labs, Airbyte, Grafana, ClickHouse, Astronomer |
| EU MNCs | 25 | SAP, Siemens, Bosch, BMW, ASML, Philips, Booking.com, Adyen, Zalando, Spotify |
| EU Tech Leaders | 32 | Celonis, N26, Bolt, Wise, UiPath, JetBrains, Delivery Hero, HelloFresh, Criteo |
| India — MNCs | 10 | TCS, Infosys, Wipro, HCL, Freshworks, Zoho, Flipkart |
| India — Product/Unicorns | 18 | Swiggy, Zomato, Razorpay, PhonePe, CRED, Meesho, Postman, Darwinbox |
| Japan Big Tech | 20 | Sony, Toyota, Rakuten (English!), Fujitsu, Mercari, NEC, Hitachi, Line Corp |
| AU/NZ | 25 | Atlassian, Canva, Xero, WiseTech, REA Group, SafetyCulture, Culture Amp, SEEK |
| Global Remote | 15 | GitLab, Automattic, Remote.com, Deel, Grafana, Miro, Notion, Linear |

### Failure Logging

All scraper failures now write to `data/scraper_errors.log`:
```
[2026-06-10 09:15 UTC] SOURCE=Indeed India | DETAIL=Bangalore | ERROR=SIGALRM timeout after 45s
[2026-06-10 09:18 UTC] SOURCE=Indeed Japan | DETAIL=Tokyo | ERROR=ConnectionError: ...
```

Check this log after each run to see which sources are blocked. Over time, patterns
in the log tell you which boards to deprioritize and which to replace with alternatives.

### Why FAANG/MNCs Belong in the List Unconditionally

These companies are not "nice to have" — they are mandatory targets regardless of portfolio
theme fit because:
1. They **always hire** data/AI engineers in bulk (hundreds of roles per quarter)
2. They have **established EU Blue Card sponsorship processes** — not speculative
3. They operate in **every target region** — Google has offices in Dublin, Munich, Bangalore,
   Sydney, Tokyo simultaneously
4. Even if your portfolio theme doesn't match, **every large tech company needs data platform
   engineers** — Kafka, Spark, dbt, pipelines, monitoring
5. **Competition is lower than you think** for non-US candidates applying to EU offices
   of US companies — US candidates rarely apply to EU offices

The scoring system will naturally rank portfolio-aligned companies higher. But FAANG still
scores well because: AI tech stack (+30) + confirmed visa sponsor (+25) + EU geo (+15) = 70
before any other signal. They belong in the top 500.

### Pending From This Session

9. **Add Naukri.com scraper** — India's real job board, needs `requests` + BeautifulSoup
   + realistic headers + random delays. Not blocked if done carefully.
10. **Add StepStone scraper** — Europe's largest job board. Needs similar careful approach.
11. **Add India VC portfolio pages** — Accel India, Peak XV (Sequoia India), Matrix Partners,
    Blume Ventures — all have public portfolio pages, same pattern as EU VC scraper.
12. **Expand static list to 500+** — currently 211. Another 200-300 companies can be added
    for mid-tier companies in each region.
13. **Add Wantedly scraper** — Japan startup jobs, but requires creating an account.

---

---

## Part 10 — Session 3 Changes (2026-06-10)

All items from the Part 4 / Part 9 pending lists were addressed. Here is the complete record.

### Fixed This Session

| # | File | What changed | Status |
|---|------|-------------|--------|
| 1 | `candidate_profile.py` | `get_visa_line()` now detects India terms before EU — Indian companies no longer receive "EU Blue Card eligible" line. | ✅ Done |
| 2 | `score_shortlist.py` | Shortlist cap raised from 100 → **500**. | ✅ Done |
| 3 | `scrape_eu_portals.py` | Added **10 India VC portfolio pages**: Accel India, Peak XV (Sequoia India), Matrix Partners India, Blume Ventures, Nexus Venture Partners, Lightspeed India, Kalaari Capital, Stellaris Venture Partners, Info Edge Ventures, Elevation Capital. | ✅ Done |
| 4 | `static_companies.py` | Expanded from **211 → 235** companies. Added 24 India entries in 3 categories: 10 GCCs (Microsoft IDC, Goldman Sachs India, JP Morgan, Walmart Global Tech, Uber India, LinkedIn India, Adobe India, Salesforce India, Qualcomm India, PayPal India), 8 data/analytics firms (Fractal Analytics, Tiger Analytics, LatentView, Mu Sigma, ThoughtWorks India, MathCo, Sigmoid, Quantiphi), 6 product/AI cos (Sarvam AI, Krutrim, Nykaa, Delhivery, Cars24, Urban Company). | ✅ Done |
| 5 | `scrape_naukri.py` | **NEW FILE** (287 lines). 3-tier scraper: Tier 1 = Naukri v2 API with mobile headers, Tier 2 = company sitemap XML, Tier 3 = curated seed of 34 top India Data/AI employers (always runs). | ✅ Done |
| 6 | `run_scrapers.py` | Added Naukri import and call. Fixed **premature total print** that fired mid-run (line 543 removed). Removed **duplicate final print** (line 570 removed). | ✅ Done |
| 7 | `score_shortlist.py` | Added `INDIA_TERMS` set. Added **India geo boost +15** (Marti is local — same as EU Blue Card weight). Visa block now **skipped for India companies** (no visa needed). Added **language penalty -8** for `(Learning)` languages. Expanded `HIGH_VALUE_CATEGORIES` to include all India subcategories: `india gcc`, `india data`, `india fintech`, `india product`, `india ai`, `india mnc`. | ✅ Done |
| 8 | `score_shortlist.py` | Added **Target_Roles scoring (+15)** — role explicitly mentions data/AI/engineer/analytics/platform. Added **Region_Eligibility scoring (+10)** — field says eligible/open/global/india/yes. These two fields were stored but never used in scoring. | ✅ Done |
| 9 | `send_outreach.py` | Fixed subject line — Indian companies now receive `"AI/Data Engineer — {Company} | Hyderabad-Based, Immediate Joiner"` instead of EU Blue Card subject. | ✅ Done |
| 10 | `enrich_shortlist.py` | Same subject line fix as send_outreach.py. Added `_INDIA_TERMS` set and `_subject()` helper. | ✅ Done |
| 11 | `status.py` | `classify_region()` fixed — India companies (country/city/geography) now classified as **"India"** instead of falling through to "Remote/Global". Added `INDIA_TERMS` constant. Also includes `City` field in geo lookup. | ✅ Done |
| 12 | `status.py` | `REGION_TARGETS` updated from 4 × 25% → **5 × 20%** (Europe, USA, Australia/NZ, India, Remote/Global). Section header updated to reflect 5-region plan. | ✅ Done |
| 13 | `followup.py` | **NEW FILE** — built the highest-ROI missing feature. Reads `outreach_tracker.csv`, finds Sent emails 5–14 days old with no follow-up, sends a short 3-sentence follow-up via Gmail OAuth2. Marks rows as `Status="FollowedUp"` + sets `FollowUp_Sent_At`. CLI: `--dry-run`, `--limit`, `--days-min`, `--days-max`. | ✅ Done |

### Scoring System After Session 3

Updated maximum possible score (new fields added):

| Signal | Points | Notes |
|--------|--------|-------|
| AI/Data keyword match | +30 max | Unchanged |
| Portfolio theme match | +25 max | Unchanged |
| Visa (confirmed sponsor) | +25 | Skipped for India (not needed) |
| Visa (EU Blue Card country) | +15 | Skipped for India |
| India geography | +15 | **NEW** — Marti is local, no friction |
| EU geography | +15 | Unchanged |
| Target_Roles match | +15 | **NEW** — data/AI/engineer keywords in role |
| EOR available | +10 | Unchanged |
| Australia/NZ | +10 | Unchanged |
| Region_Eligibility | +10 | **NEW** — eligible/open/global field |
| Remote | +8 | Unchanged |
| High-signal category | +8 | Now includes all India subcategories |
| Language penalty | -8 | **NEW** — (Learning) language deprioritized |
| Startup/growth stage | +5 | Unchanged |
| Hiring confidence high | +5 | Unchanged |
| YC backed | +5 | Unchanged |
| Hiring confidence medium | +2 | Unchanged |

**New max possible score: ~168 points**

### Still Pending After Session 3

In priority order:

1. **Regional quota enforcement** — `score_shortlist.py` scores correctly but doesn't enforce 20% per region. After scoring, split into 5 buckets and take top N from each to guarantee geographic balance.

2. **`status.py` Section 7 — FollowedUp status** — The outreach display section counts "Sent, Replied, Failed, Bounced" but not the new "FollowedUp" status from `followup.py`. Add "FollowedUp" to the tracker display loop.

3. **Expand `static_companies.py` to 500+** — currently 235. Another 250-300 companies can be hardcoded for mid-tier companies in each region (EU scaleups, AU/NZ hidden champions, India Series B/C startups).

4. **Hidden champion scrapers** — Mittelstand-digital.de (Germany), Nasscom Emerge 50 (India), BRW Fast 100 (AU), FD Gazellen (NL). These target your stated 10% hidden champion quota, which is otherwise not served by any current scraper.

5. **Wantedly scraper** — Japan startup jobs, English-friendly. Requires account creation. Medium effort.

6. **StepStone scraper** — Europe's largest job board. Needs careful anti-bot approach (mobile headers, random delays, sitemap-first strategy similar to Naukri Tier 2).

7. **Increase EU `results_wanted`** — Currently 30 per city in `scrape_directories.py`. Safely raise to 50. Net gain: ~1,400 more raw EU hits per run.

8. **`followup.py` → add to `run_scrapers.py` workflow** — Consider adding as optional final step, or at minimum document the daily workflow clearly in `PIPELINE.md`.

9. **Email deliverability — add Hunter.io verification before sending** (HIGH RISK if ignored):
   `guess_to_email()` in `send_outreach.py` guesses `careers@domain.com`. Bounce rates on cold
   lists are 30–50%. A spike in hard bounces will get your Gmail flagged or suspended within days.
   Fix: call Hunter.io's `/v2/email-verifier` API before each send and skip undeliverable addresses.
   Free tier is 25 verifications/month; paid is $49/month for 500. The code stub is in the
   `guess_to_email()` docstring.

10. **Send from a custom domain, not @gmail.com** — A dedicated sending domain (e.g.
    `marti@martisoura.dev`, ~$12/yr on Namecheap + free Gmail forwarding via Google Workspace
    or ImprovMX) protects your personal Gmail reputation, looks more professional, and lets you
    set up SPF/DKIM/DMARC properly. Do this before sending at any meaningful volume.

11. **LinkedIn InMail for top 20–30 targets** — For the highest-value India and EU companies
    in the shortlist, find a named contact (Engineering Manager, Tech Lead, or Technical Recruiter)
    on LinkedIn and send a 300-character personalised note instead of the automated email. Cold
    outreach to named individuals converts 3–5× better than `careers@` inboxes. Use the
    automated pipeline for the long tail (50–500 companies); use LinkedIn manually for the top tier.

---

*Last updated: 2026-06-10 (Session 3). Update this file whenever issues are raised or fixes are applied.*
