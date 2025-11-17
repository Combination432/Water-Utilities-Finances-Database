"""
EMMA API Client - Free Data Collection for Water Utilities
Electronic Municipal Market Access (EMMA) Database Client

No API keys, no authentication, no costs
Access to 700-900 water utility financial reports
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime


class EmmaClient:
    """Client for EMMA's public API - completely free to use"""

    BASE_URL = "https://emma.msrb.org"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://emma.msrb.org/',
        })

    def search_by_issuer(
        self,
        issuer_name: str,
        state: Optional[str] = None,
        document_type: str = "Annual Financial Information",
        page_size: int = 100,
        start_index: int = 0
    ) -> Dict:
        """
        Search EMMA by issuer name

        This uses EMMA's search interface to find financial reports.
        Note: The actual API endpoint may vary - this is based on observation
        of EMMA's website behavior.

        Args:
            issuer_name: Name of utility/issuer (e.g., "water", "utility")
            state: Two-letter state code (e.g., "CA")
            document_type: Type of document to search for
            page_size: Results per page (max 100)
            start_index: Starting index for pagination

        Returns:
            Dictionary with search results
        """
        # Note: EMMA's actual API structure may differ
        # This is a template based on common municipal finance APIs
        # You may need to reverse-engineer the actual endpoint

        params = {
            'issuerName': issuer_name,
            'size': page_size,
            'from': start_index,
        }

        if state:
            params['state'] = state

        if document_type:
            params['docType'] = document_type

        try:
            # This URL is illustrative - actual EMMA search may use different endpoints
            response = self.session.get(
                f"{self.BASE_URL}/Search/Search",
                params=params,
                timeout=30
            )

            # EMMA may return HTML instead of JSON
            # In that case, you'll need to parse HTML (see search_by_issuer_html method)
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            else:
                # Fall back to HTML parsing
                return self._parse_search_html(response.text)

        except requests.exceptions.RequestException as e:
            print(f"Error searching EMMA: {e}")
            return {"total": 0, "results": []}

    def _parse_search_html(self, html: str) -> Dict:
        """
        Parse EMMA search results from HTML

        EMMA's website may return HTML search results.
        This method extracts document information from the HTML.
        Requires BeautifulSoup for full implementation.

        Args:
            html: HTML content from search response

        Returns:
            Structured dictionary with results
        """
        # This is a placeholder - actual implementation would use BeautifulSoup
        # Example:
        # from bs4 import BeautifulSoup
        # soup = BeautifulSoup(html, 'html.parser')
        # results = soup.find_all('div', class_='search-result')
        # ... parse each result

        print("Warning: HTML parsing not yet implemented. Install BeautifulSoup4.")
        return {"total": 0, "results": []}

    def get_document_url(self, document_id: str) -> str:
        """
        Construct direct PDF URL from EMMA document ID

        EMMA uses a consistent URL pattern for documents.

        Args:
            document_id: EMMA document ID (e.g., "1234567890")

        Returns:
            Direct URL to PDF
        """
        # EMMA document URLs follow this pattern
        # The actual pattern may be: /ER{id}.pdf or /ShowDocument/{id}
        return f"{self.BASE_URL}/ER{document_id}.pdf"

    def download_document(self, document_id: str, save_path: str) -> bool:
        """
        Download a PDF document from EMMA

        Args:
            document_id: EMMA document ID
            save_path: Local file path to save PDF

        Returns:
            True if successful, False otherwise
        """
        pdf_url = self.get_document_url(document_id)

        try:
            print(f"Downloading from: {pdf_url}")
            response = self.session.get(pdf_url, timeout=120, stream=True)
            response.raise_for_status()

            # Verify it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                print(f"Warning: Content type is {content_type}, not PDF")

            # Write to file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = len(response.content) if hasattr(response, 'content') else 0
            print(f"✓ Downloaded: {document_id} -> {save_path} ({file_size/1024/1024:.1f} MB)")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Error downloading {document_id}: {e}")
            return False

    def search_advanced(
        self,
        issuer_name: Optional[str] = None,
        state: Optional[str] = None,
        cusip: Optional[str] = None,
        security_description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Advanced search with multiple filters

        Args:
            issuer_name: Name or partial name
            state: Two-letter state code
            cusip: 9-character CUSIP identifier
            security_description: Keywords in security description
            start_date: Start date for filings (YYYY-MM-DD)
            end_date: End date for filings (YYYY-MM-DD)

        Returns:
            List of matching documents
        """
        # This would call EMMA's advanced search endpoint
        # Implementation depends on actual EMMA API structure
        pass


class RateLimiter:
    """
    Simple rate limiter to be respectful to EMMA servers
    """

    def __init__(self, requests_per_minute: int = 30):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Maximum requests per minute (default: 30)
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = None

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        if self.last_request is not None:
            elapsed = time.time() - self.last_request
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                print(f"Rate limiting: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.last_request = time.time()


# Utility functions for common tasks

def search_water_utilities_by_state(state: str, client: EmmaClient = None) -> List[Dict]:
    """
    Find all water utilities in a specific state

    Args:
        state: Two-letter state code
        client: EmmaClient instance (creates new one if not provided)

    Returns:
        List of utilities with their documents
    """
    if client is None:
        client = EmmaClient()

    # Search for entities with "water" in their name
    results = client.search_by_issuer(
        issuer_name="water",
        state=state,
        document_type="Annual Financial Information"
    )

    return results.get('results', [])


def download_utility_history(
    utility_name: str,
    state: str,
    years: List[int],
    output_dir: str = ".",
    client: EmmaClient = None
) -> Dict[int, str]:
    """
    Download all available reports for a utility for specified years

    Args:
        utility_name: Name of the utility
        state: Two-letter state code
        years: List of fiscal years to download
        output_dir: Directory to save PDFs
        client: EmmaClient instance

    Returns:
        Dictionary mapping year -> downloaded file path
    """
    if client is None:
        client = EmmaClient()

    rate_limiter = RateLimiter(requests_per_minute=10)  # Conservative for downloads

    # Search for this utility
    results = client.search_by_issuer(
        issuer_name=utility_name,
        state=state
    )

    downloaded = {}

    for doc in results.get('results', []):
        # Extract year from document
        # This depends on how EMMA structures document metadata
        # You may need to parse the document title or fiscal year field

        fiscal_year = doc.get('fiscalYear')  # Placeholder field name

        if fiscal_year in years:
            rate_limiter.wait_if_needed()

            filename = f"{output_dir}/{utility_name.replace(' ', '_')}_{fiscal_year}.pdf"
            document_id = doc.get('documentId')

            if client.download_document(document_id, filename):
                downloaded[fiscal_year] = filename

    return downloaded


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = EmmaClient()

    print("="*60)
    print("EMMA Client - Water Utilities Financial Data")
    print("="*60)

    # Example 1: Search for California water utilities
    print("\n1. Searching for California water utilities...")
    results = search_water_utilities_by_state("CA", client)
    print(f"   Found {len(results)} documents")

    # Example 2: Try to download a specific document
    # Note: You'll need a real document ID from EMMA
    print("\n2. To download a document, use:")
    print("   client.download_document('DOCUMENT_ID', 'output.pdf')")

    print("\n" + "="*60)
    print("Note: This client requires EMMA's actual API endpoints.")
    print("Visit https://emma.msrb.org/ to explore available data.")
    print("You may need to reverse-engineer the exact API structure.")
    print("="*60)
