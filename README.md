creditcardSpendTracker/
│── config/
│ ├── credentials.json # OAuth / API credentials (gitignored)
│ ├── .env # environment variables (gitignored)
│ ├── categories.json # merchant -> category mapping
│ ├── categoryRules.json # regex/keyword rules for categorization
│ └── bankFormats.json # subject -> parser hint mapping
│
│── data/
│ ├── rawEmails/ # downloaded email attachments (PDF/HTML)
│ ├── parsed/ # CSVs and intermediate parsed files
│ ├── reports/ # generated reports (CSV/Excel/PNGs)
│ └── db.sqlite # SQLite database (gitignored)
│
│── logs/
│ ├── app.log # runtime/application logs
│ └── unparsedTransactions.csv# rows that failed parsing/categorization
│
│── src/
│ ├── emailFetcher.py # fetchEmails(), auth, download attachments
│ ├── billParser.py # dispatch to parser modules
│ ├── categorizer.py # categorizeTransactions(), load rules
│ ├── aggregator.py # aggregateSpends(), report generation
│ ├── dashboard.py # showSummary(), CLI wrappers
│ ├── utils.py # helpers (dates, normalization, hashing)
│ ├── dbManager.py # DB abstraction layer (wrap SQLite calls)
│ ├── parsers/
│ │ ├── genericPdfParser.py # fallback parser using pdfplumber
│ │ ├── hdfcParser.py # example bank parser (implement parse(filePath))
│ │ └── iciciParser.py # example bank parser
│ └── cli.py # argument parsing & main entrypoints
│
│── tests/
│ ├── golden/ # anonymized sample PDFs per bank for tests
│ └── test_parsers.py # unit tests for parsers
│
│── notebooks/ # experiments, ETL exploration
│
│── scripts/ # convenience scripts (e.g., dockerBuild.sh)
│
│── main.py # orchestrator: accepts CLI flags (fetch/parse/report)
│── requirements.txt # dependencies
│── README.md # project overview & setup
│── Dockerfile # optional: containerization
│── .gitignore



Nice — done. I merged everything into a single Ultimate Plan + Stretch Goals document so you have one canonical blueprint: Core MVPs, Advanced Enhancements, and Stretch Vision. I kept the camelCase naming convention for any function/module names.

🛠️ Credit Card Spend Tracker — Ultimate Plan + Stretch Goals
🎯 Core Philosophy (House Rules)

Iterative MVPs → always ship a working loop.

Schema-first → every component reads/writes the same transaction format.

Plugin parsers → drop-in new bank parsers.

Config-driven rules → minimal code changes for format/rule updates.

Automation-ready → logging, CLI flags, cron/Docker.

Security-first → mask/encrypt sensitive data, secrets management.

1 — Core MVPs (Production-usable path — high priority)

These are the items you must complete to get a reliable, automated product.

MVP0 — Local Bill Parsing (First Win)

Define universal transaction schema (SQLite) — include merchant, subCategory, currency, createdAt.

Implement parsers/genericPdfParser.py using pdfplumber.

Insert parsed rows into transactions table.

Validation step: compare parsed sum vs bill total; write failures to logs/unparsedTransactions.csv.

Export parsed data to /data/parsed/transactions.csv.

CLI: python main.py --parse --file path/to/file.pdf.

MVP1 — Categorization & Summaries

Create config/categories.json and config/categoryRules.json (regex/keyword rules).

Implement src/categorizer.py with categorizeTransactions(); write corrections back to categories.json.

Implement src/aggregator.py with aggregateSpends() grouping by month, quarter, card, category.

Export CSV + Excel (pivot-ready) using xlsxwriter/openpyxl.

Store uncategorized rows to logs for manual review.

MVP2 — Email Fetching (Automation)

Implement src/emailFetcher.py for Gmail (Gmail API + OAuth) with config-driven subject patterns (bankFormats.json).

Download attachments to /data/rawEmails/, save email metadata to emails table.

Dispatcher: when new file saved, trigger parsing → categorization → aggregation.

CLI flags: --fetch, --parse, --report.

MVP3 — Multi-Bank Support

Create src/parsers/ with one parser per bank (e.g., hdfcParser.py, iciciParser.py).

Use importlib in billParser.py dispatcher to load parser modules by name (from bankFormats.json).

Maintain tests/golden/ PDFs for each bank.

MVP4 — Reporting & Visualization

src/dashboard.py with showSummary() and flags like --month YYYY-MM, --quarter QN-YYYY.

Charts (matplotlib): spend over time, category breakdown. Save PNGs to /data/reports/.

Generate Excel with pivot tables & conditional formatting.

MVP5 — Smarter Categorization (Low-friction improvements)

Regex/keyword rules and interactive CLI correction flow.

Persist user corrections into categories.json automatically.

(Optional later) ML model (TF-IDF + classifier) with fallback to rules.

MVP6 — Deployment & Automation

Logging (logs/app.log), process supervisor (systemd / cron).

Dockerfile + instructions for scheduled runs.

Ensure incremental processing (only new emails/files are processed).

Hash/caching to avoid re-parsing same file.

2 — Advanced Enhancements (Stretch — medium priority)

These significantly improve robustness, UX, and maintainability.

Engineering & Architecture

dbManager.py abstraction to keep storage backend swappable (SQLite → Postgres).

Job queue pattern for event-driven flow (rq or lightweight job queue), so fetch → parse → categorize are asynchronous jobs.

Parallel parsing for bulk imports (multiprocessing or concurrent.futures).

Testing & Reliability

Golden dataset of anonymized PDFs per bank + CI (GitHub Actions) to run parser/regression tests on push.

Fuzz testing for malformed PDFs to ensure graceful failure.

Unit tests for each module and end-to-end test for pipeline.

Data Quality & Intelligence

Recurring spend detection (identify subscriptions).

Anomaly detection (rolling-average or simple z-score alerts).

Forecasting (Prophet or simple ARIMA) for next-month spend.

Duplicate detection across cards (same merchant/date/amount).

User Experience

Rich CLI using rich for formatted output & progress bars.

HTML mobile-friendly report outputs (Bootstrap).

Auto-email monthly/weekly reports (Gmail API or SMTP).

Google Sheets export integration.

Security & Privacy

Mask card numbers (store only last 4 digits).

Use .env for secrets with python-dotenv or move to a secrets manager later.

Optionally encrypt DB with sqlcipher if you plan long-term storage.

Run parsers in a sandboxed Docker container for extra safety.

3 — Stretch Vision (Long-term / optional)

High-value product features if you decide to expand beyond a personal tool.

Product & Integrations

Integrate with bank/aggregation APIs (Plaid/Salt Edge) where available — bypass PDF parsing.

Web dashboard (Flask/Streamlit/Plotly Dash) with auth.

Mobile app (Flutter/React Native) reading from backend API.

Multi-user support with RBAC (family accounts).

Extensibility & Ecosystem

Plugin marketplace for third-party parsers or exporters.

Provide simple Python API: from tracker import getMonthlySpend, getCategoryBreakdown.

Open-source the core (anonymized tests + docs) to attract contributors.

Money & Smart Features

Budgeting: set category budgets + alerts.

What-if analysis and goal tracking (save X by Y date).

Auto-suggestions for cost-cutting (e.g., recurring subscriptions not used).

4 — Operational & Developer UX

Use requirements.txt and optionally poetry for dependency management.

Provide clear README.md with setup steps (Gmail OAuth setup, running locally, Docker usage).

Create CONTRIBUTING.md and developer quickstart for adding parsers.

Add CHANGELOG.md to record breaking changes (parser updates, schema changes).

5 — Data Schema (Final recommended)
transactions(
    id INTEGER PRIMARY KEY,
    date DATE,
    description TEXT,
    merchant TEXT,
    amount REAL,
    currency TEXT,
    cardNumber TEXT,         -- masked: store last4 only
    sourceBank TEXT,
    sourceEmail TEXT,
    category TEXT,
    subCategory TEXT,
    parserUsed TEXT,
    importId INTEGER,        -- foreign key to imports table
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

imports(
    id INTEGER PRIMARY KEY,
    fileName TEXT,
    fileHash TEXT,
    emailId TEXT,
    parserUsed TEXT,
    importDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    notes TEXT
)

emails(
    id TEXT PRIMARY KEY,
    subject TEXT,
    sender TEXT,
    date TIMESTAMP,
    filePath TEXT,
    parserHint TEXT,
    importedAt TIMESTAMP
)

6 — Priority Roadmap (short)

MVP0 (parse one PDF) → immediate.

MVP1 (categorize + monthly summary) → quick value.

MVP2 (email fetch) → automation.

MVP3 (multi-bank) → scale.

MVP4 (reports + charts) → polish.

Advanced enhancements & stretch features as needed.

7 — Next concrete step (pick one)

I can immediately do one of these for you right now (pick which and I’ll produce runnable code / checklists):

A — Detailed coding checklist for MVP0 (functions, imports, example code snippets using pdfplumber + SQLite insertions).

B — Draft config/categories.json + example categoryRules.json with sample merchant → category entries and regex rules.

C — Full emailFetcher.py draft for Gmail API (OAuth flow + search + download attachments) with camelCase functions.

D — Create transactions SQLite schema + sample SQL and a small test dataset CSV you can import.

Tell me A/B/C/D (or say “do all”) and I’ll generate it now.