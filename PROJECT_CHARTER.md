# Joshua Project Data Visualization — Project Charter

## Project Overview

This project builds an **interactive web application** using the Joshua Project REST API to help missionaries research unreached people groups and explore field placement opportunities. The tool visualizes **religion, Gospel access metrics, and demographic data across global regions** with dynamic filtering, search, and detail views.

The application is built with **Plotly Dash** (Python web framework) and serves as a research platform for field strategy and missionary placement decisions. The primary audience is missionaries, organizational leadership, and research teams.

This charter aligns with the class group project guidelines, incorporating role assignments, communication structure, task breakdown, testing, code review, documentation standards, and a final presentation deliverable.

---

## Objectives & Scope

### Primary Goal
Build an interactive web application that allows missionaries and researchers to explore unreached people groups, filter by region/religion/demographic criteria, and access actionable intelligence for field placement and strategy decisions.

### Specific Features & Research Questions Addressed

**Exploration & Filtering**
1. Filter people groups by region, religion, and Bible translation status
2. Search by people group name or country
3. View detailed profiles including population, language, Gospel resources, and unreached status

**Visualizations & Insights**
1. **Religion composition by world region** — Stacked bar chart showing religious demographic concentration
2. **Population vs. Gospel access** — Scatter plot: total population vs. % Evangelical, colored by region and religion
3. **Bible translation gap analysis** — Bar chart: average Scripture access by religion and region
4. **Frontier & unreached profiles** — Table/dashboard showing highest-priority unreached groups by filtering criteria
5. **Geographic visualization** — Optional choropleth or marker maps for spatial exploration

**Research Questions**
- Where is Islam/Hinduism/Buddhism most concentrated, and what is their Gospel access?
- Which unreached people groups have the largest populations?
- Where is Scripture translation most lacking?
- Which regions have the highest concentration of frontier unreached people groups?
- How do demographic and Gospel access trends vary across the 12 world regions?

### Out of Scope (v1)
- Time-series / trend analysis (the API is a current snapshot, not historical)
- User authentication / roles (open research tool)
- Machine learning or predictive modeling
- Data export / reporting workflows (v2+)

---

## Roles & Responsibilities

Assign these based on each teammate's strengths and learning goals. One person can hold multiple roles on a small team.

| Role | Responsibilities |
|---|---|
| **Backend / Data Engineer** | Owns `fetch.py` and `clean.py`; API integration, caching, data transformation, and data validation |
| **Frontend / App Developer** | Owns `app.py` (Dash layout and callbacks); builds interactive UI, filters, and detail views |
| **Visualization Engineer** | Designs and implements Plotly charts within Dash; owns color schemes, axes, annotations |
| **Documentation Lead** | Maintains README, docstrings, setup guide, and API documentation; ensures code clarity |
| **QA / Testing Lead** | Writes unit tests for data pipeline; validates API responses; performs manual testing of UI flows |
| **Project Manager** | Tracks task board (GitHub Projects), runs standups, manages milestones and deadlines |

> Roles are collaborative, not siloed — everyone reviews each other's code.

---

## Data Sources

**API:** Joshua Project REST API v1
**Base URL:** `https://api.joshuaproject.net/v1/`
**Format:** JSON
**Auth:** API key passed as a query parameter (`?api_key=YOUR_KEY`)
**Cost:** Free (requires email-verified account at api.joshuaproject.net)

### Key Endpoints

| Endpoint | What It Returns |
|---|---|
| `/people_groups.json` | All people groups in all countries (primary dataset) |
| `/people_groups/daily_unreached.json` | Today's featured unreached group (useful for testing) |
| `/countries.json` | Country-level aggregates |
| `/regions.json` | Region-level aggregates |

### Key Fields Used

| Field | Description |
|---|---|
| `RegionName` | One of 12 global regions |
| `PrimaryReligion` | Dominant religion of the people group |
| `PCIslam`, `PCHinduism`, `PCBuddhism` | % of group practicing each religion |
| `PercentEvangelical` | % of group who are Evangelical |
| `Population` | Population in the given country |
| `LeastReached` | Boolean — is this group unreached? |
| `BibleStatus` | 0–5 scale of Bible translation progress |
| `HasJesusFilm` | Boolean — Jesus Film access |
| `Latitude`, `Longitude` | For map plotting |
| `Frontier` | Is this a Frontier Unreached People Group? |

---

## Deliverables

### Application Deliverables

| Component | Owner | Status |
|---|---|---|
| **Dash Web App** (`app.py`) | Frontend Developer | Interactive dashboard with filters, search, and detail views |
| **Data Pipeline** (`fetch.py`, `clean.py`) | Backend Engineer | API integration, caching, data transformation |
| **Interactive Filters** | Frontend Developer | Region, Religion, Bible Status, Unreached Status dropdowns |
| **Embedded Charts** | Visualization Engineer | 3–4 Plotly visualizations (stacked bar, scatter, etc.) |
| **Detail Panel** | Frontend Developer | Pop-up/modal showing full profile of selected people group |
| **Search Functionality** | Frontend Developer | Search by people group name or country |

### Chart Deliverables (Embedded in Web App)

| Chart | Description | Library |
|---|---|---|
| 1 | Religion composition by world region | Stacked bar chart (Plotly) |
| 2 | Population vs. % Evangelical | Scatter plot (Plotly) |
| 3 | Bible translation access by religion | Bar chart (Plotly) |
| 4 | Unreached people groups by region | Horizontal bar or table (Plotly/HTML) |

### Process & Documentation Deliverables

| Deliverable | Owner | Notes |
|---|---|---|
| Project Charter (this document) | Project Manager | Living document, updated as scope changes |
| Setup Guide | Documentation Lead | Step-by-step local setup for all team members |
| README.md | Documentation Lead | Architecture, feature overview, running the app |
| Code docstrings | All | Comprehensive function/class documentation |
| Unit tests | QA Lead | Test coverage for `fetch.py` and `clean.py` |
| User guide / demo video | Project Manager | How to use the web app for research |
| Final presentation | Project Manager | Project overview, demo, lessons learned |
| README.md | Documentation Lead | Setup instructions, project summary, attribution |
| Inline docstrings on all functions | All | Required before code review approval |
| Unit tests for `fetch.py` and `clean.py` | QA Lead | `pytest`, targeting data shape and type validation |
| Code review sign-off before merging | All | Use GitHub Pull Requests |
| Final presentation / demo | All | See Final Presentation section below |

---

## Task Breakdown & Suggested Milestones

| Phase | Tasks | Goal |
|---|---|---|
| **Phase 1 — Setup** | Repo, `.env`, virtual env, `requirements.txt`, folder structure | Everyone can run the project locally |
| **Phase 2 — Data Access** | Write `fetch.py`, test daily_unreached endpoint, cache raw JSON | Confirmed API connection |
| **Phase 3 — Data Cleaning** | Write `clean.py`, load into pandas DataFrame, handle nulls and types | Clean dataset ready for analysis |
| **Phase 4 — Exploration** | Jupyter notebook: explore distributions, check field ranges, spot anomalies | Team understands the data |
| **Phase 5 — Visualizations** | Build each of the 4 charts in `visualize.py` | Core deliverables complete |
| **Phase 6 — Testing & Review** | Write unit tests, conduct code reviews via PRs, fix issues | Code quality verified |
| **Phase 7 — Documentation** | Finalize README, docstrings, and any inline comments | Project is understandable to an outsider |
| **Phase 8 — Presentation** | Build slides or live demo, rehearse walkthrough | Ready to present |

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.11+ | Primary language |
| `requests` | API calls |
| `pandas` | Data cleaning and transformation |
| `matplotlib` / `seaborn` | Static charts |
| `plotly` | Interactive charts and choropleth maps |
| `python-dotenv` | Secure API key loading from `.env` |
| `pytest` | Unit testing |
| `jupyter` | Exploratory analysis notebooks |
| Git + GitHub (private repo) | Version control and collaboration |
| VSCode | Local development environment |
| GitHub Projects or Trello | Task tracking |

---

## Communication Plan

- **Standup cadence:** Agree on a frequency (e.g., twice weekly async check-in via Slack/text, or a weekly sync meeting)
- **Task tracking:** Use GitHub Projects (built into your repo) or Trello to assign tasks and mark progress
- **Code changes:** All changes go through a Pull Request — no direct commits to `main`
- **Blockers:** Flag in the group chat same-day; don't sit on a blocker for more than 24 hours

---

## Code Review Process

Before any code is merged into `main`:
1. Open a Pull Request (PR) on GitHub with a description of what changed and why
2. At least one other teammate reviews the code and leaves comments
3. Reviewer checks: Does it work? Is it documented? Does it follow naming conventions? Are there tests?
4. Author addresses comments, then reviewer approves and merges

---

## Testing Plan

- **Unit tests** live in a `/tests/` folder using `pytest`
- `test_fetch.py` — validates that API responses return expected keys and data types
- `test_clean.py` — validates that the cleaned DataFrame has expected columns, no unexpected nulls, correct value ranges (e.g., percentages between 0–100)
- Run tests with `pytest tests/` before opening any PR
- Goal is not 100% coverage, but coverage of all data-critical functions

---

## Documentation Standards

- Every function in `src/` must have a docstring explaining: what it does, its parameters, and what it returns
- `README.md` must include: project summary, setup instructions, how to run the scripts, and Joshua Project attribution
- Notebooks are labeled sequentially (`01_exploration.ipynb`, `02_charts_draft.ipynb`) and include markdown cells explaining what each section is doing

---

## Final Presentation

Per the class guidelines, the project concludes with a presentation or demo covering:

1. **Project overview** — what question we set out to answer and why
2. **Data walkthrough** — what the Joshua Project API provides, how we accessed and cleaned it
3. **Live demo or screenshots** — walk through each of the 4 visualizations with commentary on what they reveal
4. **Challenges & solutions** — e.g., API pagination, handling null values, choosing the right chart type
5. **Future enhancements** — what would v2 include? (e.g., Flask dashboard, additional filters, downloadable datasets for deeper time-series analysis)

Suggested format: Google Slides or PowerPoint with a live Python demo if feasible.

---

## Repository Structure

```
joshua-project-viz/
├── .env                    # API key — NEVER committed to Git
├── .env.example            # Safe template showing required variable names
├── .gitignore
├── README.md
├── requirements.txt
├── data/
│   └── cache/              # Cached raw JSON from API (committed so team can work offline)
├── notebooks/
│   ├── 01_exploration.ipynb
│   └── 02_charts_draft.ipynb
├── src/
│   ├── fetch.py            # API call functions
│   ├── clean.py            # Data cleaning and transformation
│   └── visualize.py        # Chart generation functions
├── tests/
│   ├── test_fetch.py
│   └── test_clean.py
└── outputs/
    └── charts/             # Saved PNG/HTML chart files
```

---

## Team Agreements

- API keys live in `.env` only — no exceptions, no screenshots of keys in group chats
- Raw data is cached in `data/cache/` and committed to the repo so teammates can work offline without hitting the API
- Notebooks are for exploration only; finalized, reusable logic gets refactored into `src/`
- All charts are saved to `outputs/charts/` with descriptive filenames (e.g., `scatter_population_vs_evangelical.html`)
- No direct commits to `main` — all changes go through a Pull Request

---

## Constraints & Notes

- **Rate limiting:** Not heavily documented by Joshua Project. Cache all responses locally during development.
- **Terms of Use:** Joshua Project requests attribution when displaying their data. Include a credit line in any shared outputs.
- **Photo/map assets:** The API returns asset URLs — link to them rather than downloading and storing them.

---

*Last updated: April 2026*
