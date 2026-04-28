import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.joshuaproject.net/v1"
TIMEOUT = 30

# IMPORTANT:
# Joshua Project's docs confirm the API key + /v1/... pattern,
# but you should verify these exact resource paths in the live docs
# once your team finalizes the API requests to use.
#
# These are written as clean placeholders based on the doc structure
# and expected resource naming.
COUNTRIES_ENDPOINT = "/countries.json"
PEOPLE_GROUPS_ENDPOINT = "/people_groups.json"   # verify in docs if needed

# Toggle this to True if you want to demo without a live API key.
USE_MOCK_DATA = False


# ============================================================
# MOCK DATA (for demo / fallback)
# ============================================================

MOCK_COUNTRIES = [
    {
        "Ctry": "India",
        "ISO3": "IND",
        "Continent": "Asia",
        "Population": 1420000000,
        "PrimaryReligion": "Hinduism",
    },
    {
        "Ctry": "Brazil",
        "ISO3": "BRA",
        "Continent": "South America",
        "Population": 203000000,
        "PrimaryReligion": "Christianity",
    },
    {
        "Ctry": "Nigeria",
        "ISO3": "NGA",
        "Continent": "Africa",
        "Population": 223000000,
        "PrimaryReligion": "Islam / Christianity",
    },
]

MOCK_PEOPLE_GROUPS = {
    "IND": [
        {
            "PeopNameInCountry": "Hindi, Standard",
            "Population": 350000000,
            "PrimaryReligion": "Hinduism",
            "PercentEvangelical": 0.4,
            "JPScaleText": "Unreached",
            "PrimaryLanguageName": "Hindi",
            "LeastReached": "Y",
        },
        {
            "PeopNameInCountry": "Bengali",
            "Population": 97000000,
            "PrimaryReligion": "Islam",
            "PercentEvangelical": 0.2,
            "JPScaleText": "Unreached",
            "PrimaryLanguageName": "Bengali",
            "LeastReached": "Y",
        },
        {
            "PeopNameInCountry": "Tamil",
            "Population": 76000000,
            "PrimaryReligion": "Hinduism",
            "PercentEvangelical": 1.8,
            "JPScaleText": "Minimally Reached",
            "PrimaryLanguageName": "Tamil",
            "LeastReached": "N",
        },
        {
            "PeopNameInCountry": "Punjabi",
            "Population": 35000000,
            "PrimaryReligion": "Sikhism",
            "PercentEvangelical": 0.3,
            "JPScaleText": "Unreached",
            "PrimaryLanguageName": "Punjabi",
            "LeastReached": "Y",
        },
    ],
    "BRA": [
        {
            "PeopNameInCountry": "Brazilian Portuguese",
            "Population": 170000000,
            "PrimaryReligion": "Christianity",
            "PercentEvangelical": 27.4,
            "JPScaleText": "Reached",
            "PrimaryLanguageName": "Portuguese",
            "LeastReached": "N",
        },
        {
            "PeopNameInCountry": "Guarani",
            "Population": 1800000,
            "PrimaryReligion": "Christianity",
            "PercentEvangelical": 11.0,
            "JPScaleText": "Reached",
            "PrimaryLanguageName": "Guarani",
            "LeastReached": "N",
        },
    ],
    "NGA": [
        {
            "PeopNameInCountry": "Hausa",
            "Population": 54000000,
            "PrimaryReligion": "Islam",
            "PercentEvangelical": 0.1,
            "JPScaleText": "Unreached",
            "PrimaryLanguageName": "Hausa",
            "LeastReached": "Y",
        },
        {
            "PeopNameInCountry": "Yoruba",
            "Population": 45000000,
            "PrimaryReligion": "Christianity",
            "PercentEvangelical": 18.0,
            "JPScaleText": "Reached",
            "PrimaryLanguageName": "Yoruba",
            "LeastReached": "N",
        },
        {
            "PeopNameInCountry": "Igbo",
            "Population": 32000000,
            "PrimaryReligion": "Christianity",
            "PercentEvangelical": 21.0,
            "JPScaleText": "Reached",
            "PrimaryLanguageName": "Igbo",
            "LeastReached": "N",
        },
    ],
}


# ============================================================
# HELPERS
# ============================================================

def get_api_key() -> Optional[str]:
    """
    Read API key from Streamlit secrets or environment variable.
    """
    api_key = None

    try:
        api_key = st.secrets.get("JOSHUA_PROJECT_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("JOSHUA_PROJECT_API_KEY")

    return api_key


def format_number(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "N/A"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def api_get(endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generic GET request to Joshua Project API.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key not found. Add JOSHUA_PROJECT_API_KEY to secrets.toml or environment variables.")

    full_params = {"api_key": api_key, **params}
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(url, params=full_params, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some APIs return an object wrapper; normalize to list if needed.
        for _, value in data.items():
            if isinstance(value, list):
                return value
        return [data]

    return []


def mock_find_country(country_name: str) -> Optional[Dict[str, Any]]:
    country_name = country_name.strip().lower()
    for country in MOCK_COUNTRIES:
        if country["Ctry"].lower() == country_name:
            return country
    return None


def mock_get_people_groups(iso3: str) -> List[Dict[str, Any]]:
    return MOCK_PEOPLE_GROUPS.get(iso3.upper(), [])


def find_country_live(country_name: str) -> Optional[Dict[str, Any]]:
    """
    Tries to find a country record.
    You may need to adjust the parameter names based on the exact endpoint docs.
    """
    candidates = [
        {"Ctry": country_name},
        {"country": country_name},
        {"name": country_name},
    ]

    for params in candidates:
        try:
            results = api_get(COUNTRIES_ENDPOINT, params)
            if results:
                # Prefer exact or close matches if possible
                normalized = country_name.strip().lower()
                exact = [r for r in results if str(r.get("Ctry", "")).strip().lower() == normalized]
                return exact[0] if exact else results[0]
        except requests.HTTPError:
            continue
        except Exception:
            continue

    return None


def get_people_groups_live(country: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetches people groups for a country.
    Adjust params once your team confirms the exact Joshua Project endpoint.
    """
    possible_params = []

    if country.get("ISO3"):
        possible_params.extend([
            {"ISO3": country["ISO3"]},
            {"iso3": country["ISO3"]},
            {"country": country["ISO3"]},
        ])

    if country.get("Ctry"):
        possible_params.extend([
            {"Ctry": country["Ctry"]},
            {"country": country["Ctry"]},
        ])

    for params in possible_params:
        try:
            results = api_get(PEOPLE_GROUPS_ENDPOINT, params)
            if results:
                return results
        except requests.HTTPError:
            continue
        except Exception:
            continue

    return []


def find_country(country_name: str) -> Optional[Dict[str, Any]]:
    if USE_MOCK_DATA:
        return mock_find_country(country_name)
    return find_country_live(country_name)


def get_people_groups(country: Dict[str, Any]) -> List[Dict[str, Any]]:
    if USE_MOCK_DATA:
        return mock_get_people_groups(country.get("ISO3", ""))
    return get_people_groups_live(country)


def build_people_groups_df(groups: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for g in groups:
        rows.append({
            "People Group": g.get("PeopNameInCountry", "Unknown"),
            "Population": safe_float(g.get("Population")),
            "Primary Religion": g.get("PrimaryReligion", "Unknown"),
            "Primary Language": g.get("PrimaryLanguageName", "Unknown"),
            "Percent Evangelical": safe_float(g.get("PercentEvangelical")),
            "Status": g.get("JPScaleText", g.get("JPScale", "Unknown")),
            "Least Reached": g.get("LeastReached", "N"),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(by="Population", ascending=False).reset_index(drop=True)

    return df


def religion_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Primary Religion", "Population"])

    summary = (
        df.groupby("Primary Religion", dropna=False)["Population"]
        .sum()
        .reset_index()
        .sort_values(by="Population", ascending=False)
    )
    return summary


def status_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Status", "Count"])

    summary = (
        df.groupby("Status", dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values(by="Count", ascending=False)
    )
    return summary


def plot_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str, rotate_xticks: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df[x_col], df[y_col])
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

    if rotate_xticks:
        plt.xticks(rotation=45, ha="right")

    st.pyplot(fig)


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(page_title="Joshua Project Country Dashboard", layout="wide")

st.title("Joshua Project Country Dashboard")
st.write(
    "Enter a country to explore people groups, religions, and population-related information."
)

with st.sidebar:
    st.header("Settings")
    st.write("Use mock data if you don't have your API key yet.")
    use_mock_checkbox = st.checkbox("Use mock data", value=USE_MOCK_DATA)
    USE_MOCK_DATA = use_mock_checkbox

    st.markdown("### API Key Setup")
    st.code(
        '[general]\n'
        'JOSHUA_PROJECT_API_KEY = "YOUR_KEY_HERE"',
        language="toml"
    )

country_input = st.text_input("Country name", value="India")

search_clicked = st.button("Search")

if search_clicked:
    if not country_input.strip():
        st.warning("Please enter a country name.")
        st.stop()

    with st.spinner("Loading country data..."):
        try:
            country = find_country(country_input)

            if not country:
                st.error("Country not found. Try another spelling or use mock data.")
                st.stop()

            groups = get_people_groups(country)
            df = build_people_groups_df(groups)

        except requests.HTTPError as e:
            st.error(f"API request failed: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.stop()

    st.subheader("Country Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Country", country.get("Ctry", "N/A"))
    col2.metric("ISO3", country.get("ISO3", "N/A"))
    col3.metric("Continent", country.get("Continent", "N/A"))
    col4.metric("Population", format_number(country.get("Population")))

    if df.empty:
        st.warning("No people-group records were returned for this country.")
        st.stop()

    total_groups = len(df)
    total_population = df["Population"].sum()
    unreached_count = int((df["Least Reached"] == "Y").sum())
    avg_evangelical = df["Percent Evangelical"].mean()

    st.subheader("Key Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("People Groups", f"{total_groups:,}")
    m2.metric("Population in Results", format_number(total_population))
    m3.metric("Least Reached Groups", f"{unreached_count:,}")
    m4.metric("Avg % Evangelical", f"{avg_evangelical:.2f}%")

    left, right = st.columns(2)

    with left:
        st.subheader("Top Religions by Population")
        religion_df = religion_summary(df).head(10)
        if not religion_df.empty:
            plot_bar_chart(
                religion_df,
                x_col="Primary Religion",
                y_col="Population",
                title="Population by Religion",
                rotate_xticks=True
            )

    with right:
        st.subheader("People Group Status Breakdown")
        status_df = status_summary(df)
        if not status_df.empty:
            plot_bar_chart(
                status_df,
                x_col="Status",
                y_col="Count",
                title="People Group Status Counts",
                rotate_xticks=True
            )

    st.subheader("Top People Groups by Population")
    top_groups_df = df[["People Group", "Population"]].head(10)
    if not top_groups_df.empty:
        plot_bar_chart(
            top_groups_df,
            x_col="People Group",
            y_col="Population",
            title="Top 10 People Groups",
            rotate_xticks=True
        )

    st.subheader("People Group Table")

    display_df = df.copy()
    display_df["Population"] = display_df["Population"].apply(format_number)
    display_df["Percent Evangelical"] = display_df["Percent Evangelical"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, use_container_width=True)