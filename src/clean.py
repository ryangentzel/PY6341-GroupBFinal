"""
clean.py
--------
Loads raw people group data from the Joshua Project API (via fetch.py)
and transforms it into a clean pandas DataFrame ready for visualization.

Run this file directly to test: python src/clean.py
"""

import pandas as pd
from .fetch import fetch_people_groups


# ── Column selection ──────────────────────────────────────────────────────────
# These are the only fields we need from the full API response.
# The JP API returns ~200 fields per record — we keep just what the tool uses.

KEEP_COLUMNS = [
    "PeopNameInCountry",   # People group name (in the country they reside)
    "Ctry",                # Country name
    "RegionName",          # One of 12 JP world regions
    "PrimaryReligion",     # Dominant religion (string label)
    "PercentEvangelical",  # % of group that is Evangelical (float, 0–100)
    "Population",          # Population count in that country
    "Latitude",            # For map plotting
    "Longitude",           # For map plotting
    "BibleStatus",         # 0–5 scale of Bible translation completeness
    "JPScale",             # 1–6 Gospel progress scale (1=least reached)
    "LeastReached",        # Boolean-ish: "Y" or "N"
    "Frontier",            # Boolean-ish: "Y" or "N" (< 0.1% evangelical)
    "PrimaryLanguageName", # Primary language spoken
    "HasJesusFilm",        # Boolean-ish: "Y" or "N"
    "JPScalePC",           # JP progress scale as a percentage label
    "PeopleID3",           # Unique JP people group ID (useful for linking)
    "ROL3",                # Language code (ISO 639-3)
]


# ── Bible status labels ───────────────────────────────────────────────────────
# The API returns an integer 0–5. We map these to human-readable labels
# for display in the detail panel and charts.

BIBLE_STATUS_LABELS = {
    0: "Unspecified",
    1: "No scripture",
    2: "Portions",
    3: "New Testament",
    4: "Bible portions",
    5: "Complete Bible",
}


def load_and_clean() -> pd.DataFrame:
    """
    Fetch all people groups from the Joshua Project API (or cache),
    select relevant columns, fix data types, and return a clean DataFrame.

    Returns
    -------
    pd.DataFrame
        One row per people group per country. Key columns:
        PeopNameInCountry, Ctry, RegionName, PrimaryReligion,
        PercentEvangelical, Population, Latitude, Longitude,
        BibleStatus, BibleStatusLabel, LeastReached, Frontier,
        PrimaryLanguageName, HasJesusFilm, JPScale, PeopleID3
    """
    print("Loading people groups data...")
    raw = fetch_people_groups()
    print(f"  Raw records: {len(raw):,}")

    df = pd.DataFrame(raw)

    # ── 1. Keep only the columns we need ─────────────────────────────────────
    # Some columns may not exist if the API schema changes — we only keep
    # what's actually present to avoid KeyErrors.
    available = [col for col in KEEP_COLUMNS if col in df.columns]
    missing = [col for col in KEEP_COLUMNS if col not in df.columns]
    if missing:
        print(f"  Warning: these expected columns were not found: {missing}")
    df = df[available].copy()

    # ── 2. Fix numeric types ──────────────────────────────────────────────────
    # The API returns numbers as strings in some cases. We coerce to float/int,
    # turning unparseable values into NaN rather than crashing.
    df["PercentEvangelical"] = pd.to_numeric(df["PercentEvangelical"], errors="coerce")
    df["Population"] = pd.to_numeric(df["Population"], errors="coerce")
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["BibleStatus"] = pd.to_numeric(df["BibleStatus"], errors="coerce")
    df["JPScale"] = pd.to_numeric(df["JPScale"], errors="coerce")

    # ── 3. Fill missing evangelical percentages with 0 ───────────────────────
    # NaN here would silently drop rows from our threshold filter.
    # A missing value almost certainly means no known evangelical presence.
    df["PercentEvangelical"] = df["PercentEvangelical"].fillna(0.0)

    # ── 4. Normalize boolean-ish fields ──────────────────────────────────────
    # JP returns "Y"/"N" strings. We convert to True/False for easy filtering.
    for col in ["LeastReached", "Frontier", "HasJesusFilm"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper() == "Y"

    # ── 5. Add human-readable Bible status label ──────────────────────────────
    df["BibleStatusLabel"] = (
        df["BibleStatus"]
        .map(BIBLE_STATUS_LABELS)
        .fillna("Unspecified")
    )

    # ── 6. Drop rows missing critical fields ──────────────────────────────────
    # Rows without coordinates or population are not usable in our charts.
    before = len(df)
    df = df.dropna(subset=["Latitude", "Longitude", "Population"])
    dropped = before - len(df)
    if dropped > 0:
        print(f"  Dropped {dropped:,} rows missing coordinates or population.")

    # ── 7. Build a JP profile URL for each people group ──────────────────────
    # The Joshua Project profile URL pattern uses the PeopleID3 field.
    if "PeopleID3" in df.columns:
        df["JPProfileURL"] = (
            "https://joshuaproject.net/people_groups/"
            + df["PeopleID3"].astype(str)
        )
    else:
        df["JPProfileURL"] = "https://joshuaproject.net"

    # ── 8. Reset index ────────────────────────────────────────────────────────
    df = df.reset_index(drop=True)

    print(f"  Clean records: {len(df):,}")
    print(f"  Regions: {sorted(df['RegionName'].dropna().unique())}")
    print(f"  Religions: {sorted(df['PrimaryReligion'].dropna().unique())}")
    return df


def summarize(df: pd.DataFrame) -> None:
    """
    Print a quick summary of the cleaned DataFrame.
    Useful for sanity-checking the data before building charts.

    Parameters
    ----------
    df : pd.DataFrame
        The cleaned DataFrame from load_and_clean()
    """
    print("\n── Dataset summary ───────────────────────────────────────")
    print(f"  Total people groups : {len(df):,}")
    print(f"  Unreached (LeastReached=True) : {df['LeastReached'].sum():,}")
    print(f"  Frontier groups : {df['Frontier'].sum():,}")
    print(f"  Median % Evangelical : {df['PercentEvangelical'].median():.2f}%")
    print(f"  Total population covered : {df['Population'].sum():,.0f}")
    print(f"\n  Records per region:")
    region_counts = df["RegionName"].value_counts()
    for region, count in region_counts.items():
        print(f"    {region:<40} {count:>5,}")
    print("──────────────────────────────────────────────────────────\n")


# ── Run directly for testing ──────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_and_clean()
    summarize(df)
    print("First 3 rows:")
    print(df[["PeopNameInCountry", "Ctry", "RegionName",
              "PrimaryReligion", "PercentEvangelical", "Frontier"]].head(3))
