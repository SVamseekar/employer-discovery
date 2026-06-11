"""
Candidate Profile — Single Source of Truth
===========================================
All CV data lives here. Every script that needs your details imports from this file.
Edit this file when your CV changes — nothing else needs updating.
"""

CANDIDATE = {
    "name": "Marti Soura Vamseekar",
    "email": "martisoura@gmail.com",
    "linkedin": "linkedin.com/in/souramarti",
    "github": "github.com/SVamseekar",
    "phone": "+91-9121661281",
    "location": "Hyderabad, India",
    "visa_status": "EU Blue Card Eligible",

    # Languages: native/fluent first, then learning ones with level
    "languages": {
        "English":  "fluent",
        "Telugu":   "native",
        "Hindi":    "fluent",
        "German":   "beginner",
        "Dutch":    "beginner",
        "Japanese": "beginner",
    },

    "relocation_targets": [
        "Germany", "Netherlands", "Ireland", "Austria",
        "Sweden", "Denmark", "Finland", "Belgium", "Switzerland"
    ],
    "role_targets": [
        "AI Engineer",
        "Data Platform Engineer",
        "Data Engineer",
        "ML Engineer",
        "Backend Engineer (AI/Data focus)",
    ],
    "education": "MSc Data Science — Merit, University of Greenwich, London (2021–2022)",
    "certification": "Microsoft Certified: Azure Data Engineer Associate (DP-203, March 2025)",
    "current_role": "SDE at Innosolv Private Limited (London, Remote) — Production RAG/LLM, GCP, Spring Boot",
    "summary": (
        "AI & Infrastructure Engineer with production experience in RAG/LLM pipelines, "
        "event-driven microservices, and cloud data platforms. MSc Data Science (University of "
        "Greenwich, London). EU Blue Card eligible, open to relocation across Germany, Netherlands, Ireland, wider EU."
    ),

    # Skills grouped for smart email personalization
    "skills": {
        "ai_genai": [
            "Google Vertex AI", "Gemini", "RAG", "FAISS", "BM25", "Cross-Encoder Reranking",
            "LangChain", "LLM Agents", "PaddleOCR", "scikit-learn", "TensorFlow"
        ],
        "cloud_infra": [
            "Azure Data Factory", "Synapse Analytics", "Databricks", "Data Lake Gen2",
            "GCP Cloud Run", "Docker", "Kubernetes", "GitHub Actions CI/CD"
        ],
        "data_engineering": [
            "Python", "PySpark", "dbt", "Apache Spark", "DuckDB", "ETL/ELT",
            "Parquet", "Power BI", "Tableau"
        ],
        "backend": [
            "Java 17", "Spring Boot 3", "FastAPI", "REST APIs", "Spring WebFlux",
            "Spring Cloud Gateway", "RabbitMQ", "WebSockets", "Flyway", "OpenAPI"
        ],
        "databases": [
            "PostgreSQL", "MongoDB", "Redis", "ChromaDB", "Supabase", "SQLite", "DuckDB"
        ],
        "frontend": [
            "TypeScript", "React 18", "React Native", "Flutter", "Tailwind CSS"
        ],
    },

    # Key projects with portfolio themes for smart email matching
    "projects": [
        {
            "name": "WorkforceGuard AI",
            "tagline": "EU Pay Transparency & Workforce Intelligence Platform",
            "url": "workforceguard-ai.vercel.app",
            "themes": [
                "eu compliance", "workforce analytics", "hr analytics", "people analytics",
                "public sector", "govtech", "data platform", "dbt", "fastapi",
                "ai governance", "labour market", "pay gap", "eu policy"
            ],
            "highlight": (
                "Full-stack analytics platform proving labour market tightness correlates "
                "with gender pay gaps (r≈+0.41) across 20 EU states. 36 dbt models, "
                "DuckDB warehouse, Random Forest 94.7% accuracy. "
                "Live at workforceguard-ai.vercel.app. Compliant with EU Pay Transparency Directive 2023/970/EU."
            ),
            "one_liner": "EU Pay Transparency compliance analytics platform — live at workforceguard-ai.vercel.app",
        },
        {
            "name": "AEQUITAS",
            "tagline": "UK Bus Transport Policy Intelligence Platform",
            "url": "github.com/SVamseekar",
            "themes": [
                "transport analytics", "smart cities", "public sector analytics",
                "geospatial", "geospatial intelligence", "policy", "govtech",
                "mobility", "urban", "infrastructure", "local government"
            ],
            "highlight": (
                "7-stage validated data pipeline processing 1.75M GTFS trips across 274,719 "
                "bus stops. FAISS RAG policy dashboard serving DfT and Local Transport "
                "Authorities. Bus Services Act 2025 compliance. 99.9993% spatial match rate."
            ),
            "one_liner": "Transport policy intelligence platform processing 1.75M trips for UK DfT — geospatial + RAG",
        },
        {
            "name": "Masova Platform",
            "tagline": "Cloud-Native Restaurant Management System",
            "url": "github.com/SVamseekar",
            "themes": [
                "fintech", "event-driven", "microservices", "spring boot",
                "distributed systems", "backend", "java", "rabbitmq",
                "compliance", "eu vat", "pos", "saas"
            ],
            "highlight": (
                "6 Spring Boot 3 / Java 21 microservices on GCP Cloud Run. 3 RabbitMQ "
                "topic exchanges, 11-state order machine, 5-country EU VAT engine with fiscal "
                "signers (Germany TSE, France NF525, Belgium FDM, Italy RT, Hungary NTCA). "
                "Real-time WebSocket tracking under 100ms."
            ),
            "one_liner": "Event-driven microservices with 5-country EU VAT engine — Java/Spring Boot on GCP",
        },
        {
            "name": "Bharat Alpha (Innosolv)",
            "tagline": "Institutional Equity Research Platform",
            "url": "",
            "themes": [
                "fintech", "rag", "llm", "ai infrastructure", "data platform",
                "algorithmic trading", "ai research", "production ml"
            ],
            "highlight": (
                "Production RAG across 305 annual report filings for 52 Nifty 50 companies. "
                "FAISS IndexFlatIP + BM25 + cross-encoder reranking pipeline. "
                "Algorithmic trading engine with Iron Condor P&L, Bucket4j rate limiter. GCP Cloud Run."
            ),
            "one_liner": "Production RAG + algorithmic trading engine — 305 annual reports, GCP, Java/Python",
        },
        {
            "name": "BillSathi",
            "tagline": "AI Bill Tracking Application",
            "url": "github.com/SVamseekar",
            "themes": [
                "ocr", "document ai", "classification", "consumer", "mobile", "fastapi"
            ],
            "highlight": (
                "Multi-engine OCR pipeline (PaddleOCR, EasyOCR, OpenCV) with LightGBM + "
                "ChromaDB + Gemini fallback across 19 spending categories. "
                "130 backend tests. Flutter frontend with FastAPI/SQLite."
            ),
            "one_liner": "Multi-engine OCR + LLM bill classification app — PaddleOCR, LightGBM, Gemini, Flutter",
        },
    ],
}

# Email signature block
SIGNATURE = f"""{CANDIDATE['name']}
{CANDIDATE['email']} | {CANDIDATE['linkedin']}
{CANDIDATE['certification']}
EU Blue Card Eligible | Open to relocation across EU"""


def get_best_project(sector: str, reason: str = "", tech_stack: str = "") -> dict:
    """Return the most thematically relevant project for a given company."""
    combined = f"{sector} {reason} {tech_stack}".lower()
    best = None
    best_score = 0
    for project in CANDIDATE["projects"]:
        score = sum(1 for theme in project["themes"] if theme in combined)
        if score > best_score:
            best_score = score
            best = project
    # Default to WorkforceGuard if nothing matches (most broadly impressive)
    return best if best_score > 0 else CANDIDATE["projects"][0]


def get_skill_overlap(tech_stack: str, max_skills: int = 4) -> list:
    """Find which CV skills appear in the company's tech stack."""
    stack_lower = tech_stack.lower()
    all_skills = []
    for group in CANDIDATE["skills"].values():
        all_skills.extend(group)
    # Sort longer matches first to prefer "Spring Boot 3" over "Spring"
    matched = [s for s in all_skills if s.lower() in stack_lower]
    return sorted(matched, key=len, reverse=True)[:max_skills]


def get_visa_line(country: str, geo: str = "", remote: str = "") -> str:
    """Return appropriate visa/relocation line for the email."""
    combined = f"{country} {geo}".lower()

    india_terms = ["india", "hyderabad", "bangalore", "bengaluru", "mumbai", "pune",
                   "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata"]
    eu_countries = ["germany", "netherlands", "ireland", "france", "sweden", "austria",
                    "denmark", "finland", "belgium", "switzerland", "norway", "europe"]

    if any(c in combined for c in india_terms):
        return (
            "I'm currently based in Hyderabad — no relocation or visa overhead on your end."
        )
    elif any(c in combined for c in eu_countries):
        return (
            "I'm EU Blue Card eligible and ready to relocate — "
            "no visa sponsorship complexity on your end."
        )
    elif remote.lower() == "yes":
        return (
            "I work fully remotely in production (currently at a London fintech) "
            "and can join a remote team immediately."
        )
    else:
        return (
            "I'm EU Blue Card eligible and open to relocation, "
            "which means zero visa friction for you."
        )


def get_language_line(language_req: str) -> str:
    """
    Return a language note for the email when a company has a non-English requirement.
    If the requirement is English/None/Unknown → returns empty string (no line added).
    If it's a language we're learning → acknowledges it honestly.
    """
    if not language_req or language_req.strip().lower() in ("", "unknown", "none", "english"):
        return ""

    # Strip any existing "(Learning)" tag the scraper may have added
    lang = language_req.replace("(Learning)", "").strip().rstrip("(").strip()

    level = CANDIDATE["languages"].get(lang, "beginner")

    if level in ("native", "fluent"):
        # Shouldn't normally hit this since we'd just not add a note for those
        return ""

    return (
        f"On the language front — I'm currently learning {lang} and am at {level} level. "
        f"I'm actively studying and committed to reaching professional proficiency. "
        f"In the meantime I'm fully productive in English."
    )
