#!/usr/bin/env python3
"""
refresh_data.py
---------------
Force refresh all cached data from the Joshua Project API.
Use this to re-fetch data when caches are stale or corrupted.

Run with:
    python refresh_data.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.fetch import fetch_people_groups, fetch_countries

if __name__ == "__main__":
    print("=" * 60)
    print("Forcing refresh of all Joshua Project API data...")
    print("=" * 60)
    
    print("\n1. Fetching people groups...")
    people_groups = fetch_people_groups(force_refresh=True)
    print(f"   ✓ Retrieved {len(people_groups):,} people group records")
    
    print("\n2. Fetching countries...")
    countries = fetch_countries(force_refresh=True)
    print(f"   ✓ Retrieved {len(countries):,} country records")
    
    print("\n" + "=" * 60)
    print("✓ Data refresh complete!")
    print("=" * 60)
    print("\nYou can now restart the app with: python app.py")
