# Joshua Project Data Visualization — Project Charter

## Project Overview

This project uses the Joshua Project REST API to pull structured data on people groups worldwide and produce research-grade visualizations exploring how **religion and Gospel access metrics vary across global regions**. The primary audience is the internal research team.

This charter aligns with the class group project guidelines, incorporating role assignments, communication structure, task breakdown, testing, code review, documentation standards, and a final presentation deliverable.

---

## Objectives & Scope

### Primary Goal
Produce a set of clear, reproducible Python-generated visualizations that surface patterns in religious demographics and evangelical access across all 12 Joshua Project world regions.

### Specific Research Questions
1. **Where is Islam/Hinduism/Buddhism most concentrated by population?**
   - Stacked bar chart: religion composition by region
   - Choropleth world map: colored by dominant religion or % Evangelical

2. **Where is evangelical presence lowest relative to population?**
   - Scatter plot: total population (x) vs. % Evangelical (y), colored by region, bubble size = number of unreached people groups per country

3. **How does Gospel resource access vary by religious bloc?**
   - Bar chart: average Bible translation status score broken down by primary religion
   - Highlights which religious populations have the least scripture access

### Out of Scope (v1)
- Time-series / trend analysis (the API is a current snapshot, not historical)
- Public-facing web deployment
- Machine learning or predictive modeling

---

## Roles & Responsibilities

Assign these based on each teammate's strengths and learning goals. One person can hold multiple roles on a small team.

| Role | Responsibilities |
|---|---|
| **Data Engineer** | Writes `fetch.py` and `clean.py`; owns API integration, caching, and data transformation |
| **Visualization Lead** | Writes `visualize.py`; owns chart design and library choices |
| **Documentation Lead** | Maintains README, docstrings, and the project wiki; ensures code is understandable |
| **QA / Testing Lead** | Writes unit tests, validates data integrity, leads code review checklist |
| **Project Manager** | Tracks task board (Trello/Asana/GitHub Projects), runs standups, manages deadlines |

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

### Code Deliverables

| # | Deliverable | Type | Library |
|---|---|---|---|
| 1 | Religion composition by world region | Stacked bar chart | `matplotlib` / `seaborn` |
| 2 | World map: % Evangelical by country | Choropleth | `plotly` |
| 3 | Population vs. % Evangelical | Scatter plot | `plotly` |
| 4 | Bible translation access by religion | Bar chart | `matplotlib` |

### Process Deliverables (Required by Guidelines)

| Deliverable | Owner | Notes |
|---|---|---|
| This project charter | Project Manager | Living document, update as scope changes |
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
