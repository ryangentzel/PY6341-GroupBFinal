import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv("Joshua_Project_API_Key")

BASE_URL = "https://api.joshuaproject.net/v1"
CACHE_DIR = Path("cache").parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
            "Joshua Project API Key not found. Make sure your .env file exists and contains Joshua Project API Key=your_key_here"
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

# Main functions to fetch data with optional force refresh

def fetch_people_groups(force_refresh: bool = False) -> list:
    """Fetch all people groups in all countries.

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