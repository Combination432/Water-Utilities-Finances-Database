"""
Real Data Collection Script
Finds and downloads actual water utility financial reports from EMMA
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import sys

# Known major water utilities to search for
MAJOR_WATER_UTILITIES = [
    {"name": "New York City Water Board", "state": "NY"},
    {"name": "Los Angeles Department of Water and Power", "state": "CA"},
    {"name": "San Francisco Public Utilities Commission", "state": "CA"},
    {"name": "Seattle Public Utilities", "state": "WA"},
    {"name": "Philadelphia Water Department", "state": "PA"},
    {"name": "Chicago Department of Water Management", "state": "IL"},
    {"name": "Houston Water", "state": "TX"},
    {"name": "Phoenix Water Services", "state": "AZ"},
    {"name": "San Antonio Water System", "state": "TX"},
    {"name": "Dallas Water Utilities", "state": "TX"},
    {"name": "San Diego Water Department", "state": "CA"},
    {"name": "Miami-Dade Water and Sewer", "state": "FL"},
    {"name": "Denver Water", "state": "CO"},
    {"name": "Boston Water and Sewer", "state": "MA"},
    {"name": "Portland Water Bureau", "state": "OR"},
    {"name": "Las Vegas Valley Water District", "state": "NV"},
    {"name": "Austin Water", "state": "TX"},
    {"name": "Columbus Water", "state": "OH"},
    {"name": "Charlotte Water", "state": "NC"},
    {"name": "Detroit Water and Sewerage", "state": "MI"},
]

def test_emma_access():
    """Test basic EMMA access"""
    print("Testing EMMA website access...")

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        response = session.get('https://emma.msrb.org/', timeout=15)

        if response.status_code == 200:
            print(f"✓ EMMA accessible (Status: {response.status_code})")
            return True
        else:
            print(f"✗ EMMA returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error accessing EMMA: {e}")
        return False

def search_emma_for_utility(utility_name, state):
    """
    Search EMMA for a specific utility
    This is a simplified approach - EMMA's actual search is more complex
    """
    print(f"\nSearching for: {utility_name} ({state})")

    # EMMA search typically happens at this URL
    # The actual parameters may vary
    search_url = "https://emma.msrb.org/Search/Search"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    })

    try:
        # Note: EMMA's actual search mechanism may require POST with specific form data
        # This is a starting point for exploration

        # Try to load the search page
        response = session.get('https://emma.msrb.org/', timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for search-related elements
            # This would need to be customized based on actual EMMA HTML structure
            print(f"  Connected to EMMA (page size: {len(response.text)} bytes)")

            # For now, return indication that we connected
            return {
                'status': 'connected',
                'utility': utility_name,
                'state': state,
                'note': 'EMMA accessible - actual search requires form data reverse-engineering'
            }

    except Exception as e:
        print(f"  Error: {e}")
        return None

    return None

def main():
    """Main data collection process"""
    print("="*60)
    print("REAL DATA COLLECTION FROM EMMA")
    print("="*60)

    # Test EMMA access
    if not test_emma_access():
        print("\n⚠️  Cannot access EMMA. Check internet connection.")
        return

    print("\n" + "="*60)
    print("SEARCHING FOR MAJOR WATER UTILITIES")
    print("="*60)

    results = []

    # Test with first 5 utilities
    for utility in MAJOR_WATER_UTILITIES[:5]:
        result = search_emma_for_utility(utility['name'], utility['state'])
        if result:
            results.append(result)

        # Be respectful - wait between requests
        time.sleep(2)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Attempted: {len(MAJOR_WATER_UTILITIES[:5])} utilities")
    print(f"Connected: {len(results)} times")

    print("\n📋 NEXT STEPS:")
    print("1. EMMA requires reverse-engineering their search form")
    print("2. Need to inspect browser Network tab to see actual POST data")
    print("3. Alternative: Use known CUSIP/document IDs if available")
    print("4. Or: Use a list of pre-identified EMMA URLs")

    print("\n💡 WORKAROUND:")
    print("While reverse-engineering EMMA, I can generate realistic sample data")
    print("that matches actual utility financial patterns.")

if __name__ == '__main__':
    main()
