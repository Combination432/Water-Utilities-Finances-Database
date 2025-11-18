"""
EMMA Web Scraper - HTML-based extraction
Since EMMA doesn't have a public API, we scrape the website
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import re
from datetime import datetime
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmmaScraper:
    """Scrapes EMMA website for water utility financial reports"""

    BASE_URL = "https://emma.msrb.org"
    SEARCH_URL = f"{BASE_URL}/Search/Search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def search_issuers(
        self,
        issuer_name: str,
        state: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search for issuers (utilities) on EMMA

        Args:
            issuer_name: Issuer name or keyword (e.g., "water")
            state: Two-letter state code
            max_results: Maximum results to return

        Returns:
            List of issuer dictionaries
        """
        # Note: EMMA's actual search form uses POST with specific parameters
        # You need to inspect the website to get exact parameter names

        params = {
            'issuerName': issuer_name,
        }

        if state:
            params['state'] = state

        try:
            logger.info(f"Searching EMMA for '{issuer_name}' in {state or 'all states'}...")

            # EMMA might use POST instead of GET
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract issuer information from search results
            issuers = self._parse_issuer_results(soup, max_results)

            logger.info(f"  Found {len(issuers)} issuers")
            return issuers

        except requests.RequestException as e:
            logger.error(f"Error searching EMMA: {e}")
            return []

    def _parse_issuer_results(self, soup: BeautifulSoup, max_results: int) -> List[Dict]:
        """
        Parse issuer search results from HTML

        This method needs to be customized based on EMMA's actual HTML structure.
        Inspect the search results page to find the correct selectors.
        """
        issuers = []

        # Example: Find all result rows (actual selectors will differ)
        # Inspect EMMA's HTML to find correct class names/structure
        result_rows = soup.find_all('tr', class_='search-result')  # Example class

        if not result_rows:
            # Try alternative selectors
            result_rows = soup.find_all('div', class_='issuer-result')

        for row in result_rows[:max_results]:
            try:
                issuer = self._extract_issuer_info(row)
                if issuer:
                    issuers.append(issuer)
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue

        return issuers

    def _extract_issuer_info(self, row) -> Optional[Dict]:
        """
        Extract issuer information from a result row

        This is a template - you'll need to adjust selectors based on actual HTML
        """
        try:
            # Example extraction (adjust based on actual HTML)
            name_elem = row.find('a', class_='issuer-name') or row.find('td', class_='issuer')
            state_elem = row.find('span', class_='state') or row.find('td', class_='state')

            if not name_elem:
                return None

            issuer_name = name_elem.text.strip()

            # Extract state if available
            state = None
            if state_elem:
                state = state_elem.text.strip()[:2]  # First 2 chars

            # Extract issuer ID/CUSIP if available
            issuer_link = name_elem.get('href', '')
            issuer_id = self._extract_id_from_url(issuer_link)

            return {
                'name': issuer_name,
                'state': state,
                'emma_issuer_id': issuer_id,
                'search_url': f"{self.BASE_URL}{issuer_link}" if issuer_link else None
            }

        except Exception as e:
            logger.debug(f"Error extracting issuer: {e}")
            return None

    def search_documents(
        self,
        issuer_name: str,
        state: Optional[str] = None,
        document_type: str = "Annual Financial Information",
        years: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Search for financial documents for an issuer

        Args:
            issuer_name: Issuer name
            state: State code
            document_type: Type of document to find
            years: List of fiscal years to filter

        Returns:
            List of document dictionaries
        """
        # Build search URL (actual parameters may differ)
        params = {
            'issuerName': issuer_name,
            'docType': document_type,
        }

        if state:
            params['state'] = state

        try:
            logger.info(f"Searching documents for '{issuer_name}'...")

            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            documents = self._parse_document_results(soup, years)

            logger.info(f"  Found {len(documents)} documents")
            return documents

        except requests.RequestException as e:
            logger.error(f"Error searching documents: {e}")
            return []

    def _parse_document_results(self, soup: BeautifulSoup, years: Optional[List[int]]) -> List[Dict]:
        """Parse document search results from HTML"""
        documents = []

        # Find document result rows (adjust selectors based on actual HTML)
        result_rows = soup.find_all('tr', class_='document-row')

        if not result_rows:
            result_rows = soup.find_all('div', class_='document-result')

        for row in result_rows:
            try:
                doc = self._extract_document_info(row)

                if doc:
                    # Filter by year if specified
                    if years:
                        if doc.get('fiscal_year') in years:
                            documents.append(doc)
                    else:
                        documents.append(doc)

            except Exception as e:
                logger.debug(f"Error parsing document: {e}")
                continue

        return documents

    def _extract_document_info(self, row) -> Optional[Dict]:
        """Extract document information from result row"""
        try:
            # Example extraction (adjust based on actual HTML)
            title_elem = row.find('a', class_='document-title')
            date_elem = row.find('span', class_='filing-date')

            if not title_elem:
                return None

            title = title_elem.text.strip()
            document_url = title_elem.get('href', '')

            # Extract document ID from URL
            # EMMA URLs are typically like: /ER1234567.pdf or /ShowDocument/ER1234567
            document_id = self._extract_document_id(document_url)

            # Extract fiscal year from title or date
            fiscal_year = self._extract_year_from_title(title)

            # Extract filing date
            filing_date = None
            if date_elem:
                date_text = date_elem.text.strip()
                filing_date = self._parse_date(date_text)

            return {
                'document_id': document_id,
                'emma_document_id': document_id,
                'title': title,
                'document_url': f"{self.BASE_URL}{document_url}" if not document_url.startswith('http') else document_url,
                'fiscal_year': fiscal_year,
                'filing_date': filing_date,
                'document_type': 'CAFR'  # Default assumption
            }

        except Exception as e:
            logger.debug(f"Error extracting document: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract ID from EMMA URL"""
        # Example patterns: /Issuer/Details/123456 or ?issuerId=123456
        patterns = [
            r'/Details/(\d+)',
            r'issuerId=(\d+)',
            r'/(\d+)$'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _extract_document_id(self, url: str) -> Optional[str]:
        """Extract document ID from URL"""
        # EMMA document IDs: ER1234567, MD123456, etc.
        patterns = [
            r'/(ER\d+)',
            r'/(MD\d+)',
            r'/([A-Z]{2}\d+)',
            r'documentId=([A-Z]{2}\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Try just numeric ID
        match = re.search(r'/(\d{7,10})', url)
        if match:
            return f"ER{match.group(1)}"

        return None

    def _extract_year_from_title(self, title: str) -> Optional[int]:
        """Extract fiscal year from document title"""
        # Look for 4-digit years
        matches = re.findall(r'\b(20\d{2})\b', title)
        if matches:
            return int(matches[0])

        # Look for FY patterns
        matches = re.findall(r'FY\s*(\d{2})', title)
        if matches:
            year_short = int(matches[0])
            return 2000 + year_short if year_short < 50 else 1900 + year_short

        return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format"""
        # Try common date formats
        formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%m-%d-%Y'
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def download_document(self, document_id: str, save_path: str) -> bool:
        """
        Download a document PDF from EMMA

        Args:
            document_id: EMMA document ID (e.g., "ER1234567")
            save_path: Local file path to save

        Returns:
            True if successful
        """
        # Construct PDF URL
        if not document_id.startswith('ER') and not document_id.startswith('MD'):
            document_id = f"ER{document_id}"

        pdf_url = f"{self.BASE_URL}/{document_id}.pdf"

        try:
            logger.info(f"Downloading {document_id}...")

            response = self.session.get(pdf_url, timeout=120, stream=True)
            response.raise_for_status()

            # Write to file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size_mb = len(response.content) / 1024 / 1024 if hasattr(response, 'content') else 0
            logger.info(f"  ✓ Downloaded {document_id} ({file_size_mb:.1f} MB)")
            return True

        except requests.RequestException as e:
            logger.error(f"  ✗ Error downloading {document_id}: {e}")
            return False

    def get_document_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of document for deduplication"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


class RateLimiter:
    """Rate limiter to be respectful to EMMA servers"""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = None

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        if self.last_request is not None:
            elapsed = time.time() - self.last_request
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

        self.last_request = time.time()


# Testing functions
if __name__ == '__main__':
    print("="*60)
    print("EMMA Scraper Test")
    print("="*60)

    scraper = EmmaScraper()

    # Test 1: Search for issuers
    print("\nTest 1: Searching for water utilities in California...")
    issuers = scraper.search_issuers("water", state="CA", max_results=5)

    print(f"Found {len(issuers)} issuers:")
    for issuer in issuers:
        print(f"  - {issuer['name']} ({issuer.get('state', 'N/A')})")

    # Test 2: Search for documents
    if issuers:
        print("\nTest 2: Searching for documents...")
        docs = scraper.search_documents(
            issuer_name=issuers[0]['name'],
            state=issuers[0].get('state'),
            years=[2022, 2023]
        )

        print(f"Found {len(docs)} documents:")
        for doc in docs[:3]:
            print(f"  - {doc['title']}")
            print(f"    ID: {doc['document_id']}")
            print(f"    Year: {doc.get('fiscal_year', 'N/A')}")

    print("\n" + "="*60)
    print("NOTE: This scraper requires manual inspection of EMMA's HTML")
    print("Visit https://emma.msrb.org/ and inspect the page source")
    print("to determine the correct CSS selectors for your version.")
    print("="*60)
