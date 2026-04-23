# Project Setup Guide
## Joshua Project Data Visualization

This guide walks every team member through setting up the project locally — from cloning the repo to making your first API call. Follow each step in order. If you get stuck, flag it in the group chat same-day.

---

## Prerequisites

Make sure you have the following installed before starting:

- **Python 3.11+** — check by running `python3 --version` in your terminal. Download at [python.org](https://python.org) if needed.
- **Git** — check by running `git --version`. Download at [git-scm.com](https://git-scm.com) if needed.
- **VSCode** — [code.visualstudio.com](https://code.visualstudio.com)
- A **GitHub account**

---

## Step 1 — Get Your Joshua Project API Key

Each team member needs their own API key.

1. Go to [https://api.joshuaproject.net](https://api.joshuaproject.net)
2. Fill out the form (name + email, it's free)
3. Check your email and click the verification link
4. Your 12-character key will appear on screen — **save it in a password manager or secure note**

> ⚠️ Your API key is like a password. You will never paste it directly into a Python file, a notebook, or a group chat. The next steps show you the safe way to use it.

---

## Step 2 — Create the Folder Structure (Project Manager does this once, commits it)

Run these commands from inside the `joshua-project-viz/` folder:

```bash
mkdir -p data/cache notebooks src tests outputs/charts

touch .env.example requirements.txt
touch src/__init__.py src/fetch.py src/clean.py src/visualize.py
touch tests/__init__.py tests/test_fetch.py tests/test_clean.py
touch notebooks/.gitkeep outputs/charts/.gitkeep
```

Your project should now look like this:

```
joshua-project-viz/
├── .env.example
├── README.md
├── requirements.txt
├── data/
│   └── cache/
├── notebooks/
├── src/
│   ├── __init__.py
│   ├── fetch.py
│   ├── clean.py
│   └── visualize.py
├── tests/
│   ├── __init__.py
│   ├── test_fetch.py
│   └── test_clean.py
└── outputs/
    └── charts/
```

---

## Step 5 — Create the .gitignore (CRITICAL — do this before your first commit)

Create `.gitignore` in the root folder and paste in the following content:

```
# === SECRETS — never commit ===
.env

# Python
__pycache__/
*.py[cod]
*.pyo
.Python
*.egg-info/
dist/
build/

# Virtual environment
.venv/
venv/
env/

# Jupyter checkpoints
.ipynb_checkpoints/

# VSCode settings
.vscode/

# macOS
.DS_Store
```

> ⚠️ The `.env` line is the critical one. It tells Git to permanently ignore your secrets file. Verify it's there before you ever run `git add .`

---

## Step 6 — Create Your .env File (Each person does this locally — it is never committed)

Create a file named exactly `.env` (note the leading dot) in the root of the project:

```bash
touch .env
```

Open it in VSCode and add this single line, replacing the placeholder with your real key:

```
JP_API_KEY=your_actual_12_character_key_here
```

Now create `.env.example` (this one IS committed — it shows teammates what variables are needed without revealing any actual values):

```
JP_API_KEY=your_joshua_project_api_key_here
```

> ✅ Rule of thumb: `.env` = real secrets, stays on your machine only. `.env.example` = template with fake values, safe to commit.

---

## Step 7 — Set Up a Python Virtual Environment (Each person does this locally)

A virtual environment keeps this project's packages separate from everything else on your computer. Think of it as a clean, isolated Python installation just for this project.

```bash
# Make sure you're in the project folder
cd joshua-project-viz

# Create the virtual environment (only need to do this once)
python3 -m venv .venv

# Activate it — you need to do this every time you open a new terminal
# On Mac/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

You'll know it's active when you see `(.venv)` at the start of your terminal prompt.

---

## Step 8 — Install Dependencies

Paste the following into `requirements.txt`:

```
requests==2.31.0
pandas==2.2.0
matplotlib==3.8.0
seaborn==0.13.0
plotly==5.18.0
python-dotenv==1.0.0
jupyter==1.0.0
pytest==7.4.0
nbformat>=4.2.0
```

Then install everything:

```bash
pip install -r requirements.txt
```

You should see packages downloading and installing. This may take a minute or two.

---

## Step 9 — Write the Fetch Module

Open `src/fetch.py` and paste in the following code. Read the comments — they explain what each part does.

```python
"""
fetch.py
--------
Handles all communication with the Joshua Project API.
Responses are cached locally as JSON files so we don't
hit the API repeatedly during development.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()
API_KEY = os.getenv("JP_API_KEY")

BASE_URL = "https://api.joshuaproject.net/v1"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"


def fetch_endpoint(endpoint: str, params: dict = None, force_refresh: bool = False) -> list:
    """
    Fetch data from a Joshua Project API endpoint.
    Results are cached locally as JSON to avoid repeated API calls.

    Parameters
    ----------
    endpoint : str
        The API path, e.g. "/people_groups.json"
    params : dict, optional
        Additional query parameters to pass (e.g. filters)
    force_refresh : bool
        If True, ignore any cached file and re-fetch from the API

    Returns
    -------
    list
        Parsed JSON response as a Python list of dicts
    """
    if API_KEY is None:
        raise ValueError(
            "JP_API_KEY not found. Make sure your .env file exists "
            "and contains JP_API_KEY=your_key_here"
        )

    # Build a safe filename from the endpoint for caching
    cache_filename = endpoint.strip("/").replace("/", "_")
    cache_path = CACHE_DIR / f"{cache_filename}.json"

    # Return cached data if it exists and we're not forcing a refresh
    if cache_path.exists() and not force_refresh:
        print(f"[cache] Loading from {cache_path}")
        with open(cache_path, "r") as f:
            return json.load(f)

    # Build request parameters
    all_params = {"api_key": API_KEY}
    if params:
        all_params.update(params)

    # Make the API request
    url = f"{BASE_URL}{endpoint}"
    print(f"[api] Fetching {url} ...")
    response = requests.get(url, params=all_params)
    response.raise_for_status()  # Raises an error for 4xx/5xx responses

    data = response.json()

    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[cache] Saved to {cache_path}")

    return data


def fetch_people_groups(force_refresh: bool = False) -> list:
    """
    Fetch all people groups in all countries.

    Returns
    -------
    list
        List of people group dicts from the API
    """
    return fetch_endpoint("/people_groups.json", force_refresh=force_refresh)


def fetch_daily_unreached() -> dict:
    """
    Fetch today's featured unreached people group.
    Useful for quick testing without pulling the full dataset.

    Returns
    -------
    dict
        A single people group record
    """
    result = fetch_endpoint("/people_groups/daily_unreached.json")
    return result[0] if result else {}
```

---

## Step 10 — Test Your API Connection

Before writing any visualization code, confirm the connection works. Create a temporary test script:

```bash
touch test_connection.py
```

Paste this in:

```python
from src.fetch import fetch_daily_unreached

group = fetch_daily_unreached()

print("✅ Connection successful!")
print(f"   People Group : {group.get('PeopNameInCountry')}")
print(f"   Country      : {group.get('Ctry')}")
print(f"   Religion      : {group.get('PrimaryReligion')}")
print(f"   % Evangelical : {group.get('PercentEvangelical')}")
```

Run it:

```bash
python test_connection.py
```

You should see a real people group printed out. If you get an error:
- `JP_API_KEY not found` → check your `.env` file exists and the variable name is spelled exactly `JP_API_KEY`
- `401 Unauthorized` → your key may be wrong or not yet verified — check your email
- `ConnectionError` → check your internet connection

Delete `test_connection.py` once the test passes — it was just a sanity check.

---

## Step 11 — Make the First Commit (Project Manager does this with the scaffolding)

```bash
# Stage all the new files
git add .

# Verify .env is NOT in the staged files before committing
git status
# You should NOT see ".env" listed — only .env.example

# Commit
git commit -m "Initial project scaffold: folder structure, fetch module, requirements"

# Push to GitHub
git push origin main
```

> ✅ If you ever accidentally commit a secret, let the team know immediately. The key needs to be rotated (request a new one from Joshua Project) and removed from Git history.

---

## Step 12 — Daily Workflow for All Teammates

Every time you sit down to work on the project:

```bash
# 1. Navigate to the project folder
cd ~/Documents/projects/joshua-project-viz

# 2. Activate the virtual environment
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows

# 3. Pull the latest changes from teammates
git pull origin main

# 4. Create a new branch for your work (never work directly on main)
git checkout -b your-name/feature-description
# Example: git checkout -b ryan/scatter-plot

# 5. Do your work...

# 6. Stage and commit your changes
git add .
git commit -m "Description of what you built or fixed"

# 7. Push your branch
git push origin your-name/feature-description

# 8. Open a Pull Request on GitHub for teammates to review
```

---

## Step 13 — Set Up GitHub Projects for Task Tracking (Project Manager)

1. In your GitHub repo, click the **Projects** tab
2. Click **New project** → choose **Board** view
3. Create columns: `Backlog`, `In Progress`, `In Review`, `Done`
4. Add a card for each task from the Phase breakdown in the charter
5. Assign cards to teammates and set labels

This replaces the need for a separate Trello account since everything is in the repo.

---

## Recommended VSCode Extensions

Install these from the Extensions panel (`Cmd+Shift+X` / `Ctrl+Shift+X`):

| Extension | Why |
|---|---|
| **Python** (Microsoft) | Syntax highlighting, IntelliSense, linting |
| **Pylance** | Type checking and better autocomplete |
| **Jupyter** | Run `.ipynb` notebooks directly in VSCode |
| **GitLens** | See who wrote what, inline blame, branch history |
| **Python Indent** | Fixes indentation automatically |
| **.env** (mikestead) | Syntax highlighting for your `.env` file |

---

## Quick Reference: Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install a new package and update requirements
pip install package-name
pip freeze > requirements.txt

# Run tests
pytest tests/

# Start a Jupyter notebook
jupyter notebook

# Check git status
git status

# Pull latest from teammates
git pull origin main

# See branches
git branch -a
```

---

## Security Checklist — Before Every Push

Run through this mentally before `git push`:

- [ ] Is `.env` listed in `.gitignore`? (check once, then trust it)
- [ ] Did I use `os.getenv("JP_API_KEY")` to load the key — not hardcode it?
- [ ] Did I run `git status` and confirm `.env` is not in the staged files?
- [ ] Are any API keys visible in my Jupyter notebook outputs? (clear outputs before committing notebooks)

---

*Setup guide last updated: April 2026*
