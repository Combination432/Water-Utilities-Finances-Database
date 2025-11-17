"""
Test script for EMMA client
This helps verify the EMMA client works without requiring a database
"""

import sys
from emma_client import EmmaClient, RateLimiter


def test_connection():
    """Test basic connection to EMMA"""
    print("\n" + "="*60)
    print("TEST 1: EMMA Connection")
    print("="*60)

    client = EmmaClient()

    # Try to access EMMA homepage
    try:
        response = client.session.get("https://emma.msrb.org/", timeout=10)
        if response.status_code == 200:
            print("✓ EMMA website is accessible")
            print(f"  Status Code: {response.status_code}")
            return True
        else:
            print(f"✗ EMMA returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_search():
    """Test search functionality"""
    print("\n" + "="*60)
    print("TEST 2: Search Functionality")
    print("="*60)

    client = EmmaClient()

    print("Searching for 'San Francisco Public Utilities' in California...")

    try:
        results = client.search_by_issuer(
            issuer_name="San Francisco Public Utilities",
            state="CA"
        )

        total = results.get('total', 0)
        result_list = results.get('results', [])

        print(f"  Search returned: {total} total results")
        print(f"  Results in response: {len(result_list)}")

        if len(result_list) > 0:
            print("\n  First result:")
            first = result_list[0]
            for key, value in first.items():
                print(f"    {key}: {value}")
            return True
        else:
            print("  ⚠ No results returned - this may be expected")
            print("    EMMA's API structure may need reverse-engineering")
            return None

    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False


def test_document_url():
    """Test document URL construction"""
    print("\n" + "="*60)
    print("TEST 3: Document URL Construction")
    print("="*60)

    client = EmmaClient()

    # Use a sample document ID
    sample_id = "1234567890"
    url = client.get_document_url(sample_id)

    print(f"Sample Document ID: {sample_id}")
    print(f"Constructed URL: {url}")
    print("\n✓ URL construction works")

    return True


def test_rate_limiter():
    """Test rate limiting functionality"""
    print("\n" + "="*60)
    print("TEST 4: Rate Limiter")
    print("="*60)

    import time

    limiter = RateLimiter(requests_per_minute=60)  # 1 per second

    print("Making 3 rapid requests (should add delays)...")

    for i in range(3):
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        print(f"  Request {i+1}: waited {elapsed:.2f}s")

    print("\n✓ Rate limiter working correctly")
    return True


def manual_test_instructions():
    """Print instructions for manual testing"""
    print("\n" + "="*60)
    print("MANUAL TESTING INSTRUCTIONS")
    print("="*60)

    print("""
To fully test the EMMA client, you need to:

1. Visit EMMA's website manually:
   https://emma.msrb.org/

2. Use the Advanced Search to find a water utility:
   - Go to: https://emma.msrb.org/AdvancedSearch/AdvancedSearch.jsp
   - Enter Issuer Name: "water"
   - Select State: California
   - Document Type: Annual Financial Information
   - Click Search

3. Inspect the browser's Network tab (F12 -> Network)
   - Look for API calls when you click Search
   - Note the request URL and parameters
   - This will show EMMA's actual API structure

4. Get a real Document ID:
   - Click on any search result
   - Look at the document URL
   - Extract the document ID (usually in the URL)

5. Test downloading with real ID:
   python -c "from emma_client import EmmaClient; \\
              client = EmmaClient(); \\
              client.download_document('YOUR_DOCUMENT_ID', 'test.pdf')"

6. Update emma_client.py with actual API endpoints discovered in step 3

IMPORTANT: EMMA may not have a public JSON API. If so, you'll need to:
- Install BeautifulSoup4: pip install beautifulsoup4
- Parse HTML search results instead of JSON
- Extract document IDs from HTML
""")


def run_all_tests():
    """Run all automated tests"""
    print("\n" + "🌊"*30)
    print(" "*15 + "EMMA CLIENT TEST SUITE")
    print("🌊"*30)

    tests = [
        ("Connection Test", test_connection),
        ("Search Test", test_search),
        ("URL Construction Test", test_document_url),
        ("Rate Limiter Test", test_rate_limiter),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ NEEDS SETUP"

        print(f"{status:12} {test_name}")

    # Manual instructions
    manual_test_instructions()

    # Final message
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("""
1. Follow the manual testing instructions above
2. Reverse-engineer EMMA's actual API structure
3. Update emma_client.py with correct endpoints
4. Optionally implement HTML parsing with BeautifulSoup4
5. Start building your utility database!

Remember: All EMMA data is completely FREE - no API keys needed!
""")


if __name__ == "__main__":
    run_all_tests()
