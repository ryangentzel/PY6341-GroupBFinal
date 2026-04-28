# Project Setup Guide
## Joshua Project Unreached People Groups Explorer (Dash Web App)

This guide walks every team member through setting up the project locally — from cloning the repo to running the interactive Dash web application. Follow each step in order. If you get stuck, flag it in the group chat same-day.

**What you'll build:** A Python-based web application that helps missionaries explore unreached people groups, filter by region/religion/Gospel access, and research field placement opportunities using Joshua Project data.

---

## Prerequisites

Make sure you have the following installed before starting:

- **Python 3.11+** — check by running `python3 --version` in your terminal. Download at [python.org](https://python.org) if needed.
- **Git** — check by running `git --version`. Download at [git-scm.com](https://git-scm.com) if needed.
- **VSCode** — [code.visualstudio.com](https://code.visualstudio.com)
- A **GitHub account**

---

## Step 1 — Create Your .env File (Each person does this locally — it is never committed)

Create a file named exactly `.env` (note the leading dot) in the root of the project:

```bash
touch .env
```

Open it in VSCode and add this single line, replacing the placeholder with your real key:

```
Joshua_Project_API_Key=youractualkeyhere
```

> ✅ Rule of thumb: `.env` = real secrets, stays on your machine only. `.env.example` = template with fake values, safe to commit.

---

## Step 2 — Set Up a Python Virtual Environment (Each person does this locally)

A virtual environment keeps this project's packages separate from everything else on your computer. Think of it as a clean, isolated Python installation just for this project.

```bash
# Make sure you're in the project folder
cd PY6341-GroupBFinal

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

## Step 3 — Install Dependencies

Paste the following into `requirements.txt`:

```
requests==2.31.0
pandas==2.2.0
matplotlib==3.8.0
seaborn==0.13.0
plotly==5.18.0
dash==2.16.1
dash-bootstrap-components==1.5.0
python-dotenv==1.0.0
jupyter==1.0.0
pytest==7.4.0
nbformat>=4.2.0
```

**Key additions:** `dash==2.16.1` and `dash-bootstrap-components==1.5.0` for the interactive web application.

```bash
pip install -r requirements.txt
```

You should see packages downloading and installing. This may take a minute or two.

---


---

## Step 4 — Test Your API Connection

Before running the full web app, confirm the API connection works. Create a temporary test script:

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
- `Joshua Project API Key not found` → check your `.env` file exists and contains `Joshua_Project_API_Key=your_key_here`
- `401 Unauthorized` → your key may be wrong or not yet verified — check your email
- `ConnectionError` → check your internet connection

Delete `test_connection.py` once the test passes — it was just a sanity check.

---

## Step 5 — Run the Web Application

Once the API test passes, you're ready to start the interactive Dash web app:

```bash
# Make sure your venv is activated
source .venv/bin/activate

# Start the app
python app.py
```

You should see output like:

```
Loading data...
  Raw records: 17,686
Data loaded.

Dash is running on http://127.0.0.1:8050

 * Serving Flask app 'app'
 * Debug mode: on
```

Open your browser to **http://127.0.0.1:8050** and you'll see the interactive dashboard with:
- Filterable dropdowns (Region, Religion, Bible Status)
- Search box for people groups
- Interactive charts showing demographics and Gospel access
- Detail panels for exploring individual people groups

Press `Ctrl+C` in your terminal to stop the app.
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
*Setup guide last updated: April 2026*
