"""
PDF Parser for Financial Reports
Uses pdfplumber to extract tables from CAFRs
"""

import pdfplumber
from typing import List, Dict, Optional, Tuple
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialPDFParser:
    """Parse financial tables from PDF reports"""

    # Keywords for identifying financial statement pages
    STATEMENT_KEYWORDS = {
        'balance_sheet': [
            'statement of net position',
            'balance sheet',
            'statement of financial position',
            'assets and liabilities'
        ],
        'income_statement': [
            'statement of revenues',
            'statement of activities',
            'income statement',
            'statement of operations',
            'revenues, expenses'
        ],
        'cash_flow': [
            'statement of cash flows',
            'cash flow statement'
        ]
    }

    def __init__(self, pdf_path: str):
        """
        Initialize parser with PDF path

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.pdf = None
        self.pages = []
        self.metadata = {}

    def open(self):
        """Open PDF file"""
        try:
            self.pdf = pdfplumber.open(self.pdf_path)
            self.pages = self.pdf.pages
            self.metadata = {
                'total_pages': len(self.pages),
                'file_size_mb': self.pdf_path.stat().st_size / 1024 / 1024
            }
            logger.info(f"Opened PDF: {self.pdf_path.name} ({self.metadata['total_pages']} pages)")
            return True
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return False

    def close(self):
        """Close PDF file"""
        if self.pdf:
            self.pdf.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def find_statement_pages(self) -> Dict[str, List[int]]:
        """
        Find pages containing financial statements

        Returns:
            Dictionary mapping statement type to list of page numbers
        """
        statement_pages = {
            'balance_sheet': [],
            'income_statement': [],
            'cash_flow': []
        }

        for page_num, page in enumerate(self.pages, start=1):
            try:
                text = page.extract_text().lower() if page.extract_text() else ""

                # Check for each statement type
                for statement_type, keywords in self.STATEMENT_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in text:
                            statement_pages[statement_type].append(page_num)
                            logger.debug(f"Found {statement_type} on page {page_num}")
                            break  # Found this type, move to next page

            except Exception as e:
                logger.debug(f"Error processing page {page_num}: {e}")
                continue

        # Log findings
        for stmt_type, pages in statement_pages.items():
            if pages:
                logger.info(f"  {stmt_type}: pages {pages}")

        return statement_pages

    def extract_tables_from_page(self, page_number: int) -> List[List[List[str]]]:
        """
        Extract all tables from a specific page

        Args:
            page_number: Page number (1-indexed)

        Returns:
            List of tables, where each table is a list of rows,
            and each row is a list of cell values
        """
        if page_number < 1 or page_number > len(self.pages):
            logger.error(f"Invalid page number: {page_number}")
            return []

        page = self.pages[page_number - 1]

        try:
            # Extract tables using pdfplumber
            tables = page.extract_tables()

            if tables:
                logger.debug(f"Found {len(tables)} tables on page {page_number}")

            # Clean up tables
            cleaned_tables = []
            for table in tables:
                cleaned_table = self._clean_table(table)
                if cleaned_table:
                    cleaned_tables.append(cleaned_table)

            return cleaned_tables

        except Exception as e:
            logger.error(f"Error extracting tables from page {page_number}: {e}")
            return []

    def _clean_table(self, table: List[List[str]]) -> List[List[str]]:
        """
        Clean and normalize table data

        Args:
            table: Raw table from pdfplumber

        Returns:
            Cleaned table
        """
        if not table:
            return []

        cleaned = []
        for row in table:
            if row:
                # Clean each cell
                cleaned_row = []
                for cell in row:
                    if cell is not None:
                        # Remove excess whitespace
                        cleaned_cell = ' '.join(str(cell).split())
                        cleaned_row.append(cleaned_cell)
                    else:
                        cleaned_row.append('')

                # Skip empty rows
                if any(cell for cell in cleaned_row):
                    cleaned.append(cleaned_row)

        return cleaned

    def extract_statement_tables(self, statement_type: str) -> List[Dict]:
        """
        Extract tables for a specific statement type

        Args:
            statement_type: 'balance_sheet', 'income_statement', or 'cash_flow'

        Returns:
            List of dictionaries containing table data and metadata
        """
        statement_pages = self.find_statement_pages()
        pages = statement_pages.get(statement_type, [])

        if not pages:
            logger.warning(f"No pages found for {statement_type}")
            return []

        results = []

        for page_num in pages:
            tables = self.extract_tables_from_page(page_num)

            for idx, table in enumerate(tables):
                results.append({
                    'statement_type': statement_type,
                    'page_number': page_num,
                    'table_index': idx,
                    'table_data': table,
                    'row_count': len(table),
                    'column_count': len(table[0]) if table else 0
                })

        logger.info(f"Extracted {len(results)} tables for {statement_type}")
        return results

    def extract_all_statements(self) -> Dict[str, List[Dict]]:
        """
        Extract all financial statements from PDF

        Returns:
            Dictionary mapping statement type to list of tables
        """
        all_statements = {}

        for statement_type in ['balance_sheet', 'income_statement', 'cash_flow']:
            tables = self.extract_statement_tables(statement_type)
            if tables:
                all_statements[statement_type] = tables

        return all_statements

    def identify_year_columns(self, header_row: List[str]) -> Dict[int, int]:
        """
        Identify which columns contain fiscal year data

        Args:
            header_row: First row of table (should contain years)

        Returns:
            Dictionary mapping column index to fiscal year
        """
        year_columns = {}

        for idx, cell in enumerate(header_row):
            # Look for 4-digit years
            years = re.findall(r'\b(20\d{2})\b', str(cell))
            if years:
                year_columns[idx] = int(years[0])

        return year_columns

    def is_financial_table(self, table: List[List[str]]) -> bool:
        """
        Determine if a table contains financial data

        Args:
            table: Table data

        Returns:
            True if table appears to contain financial data
        """
        if not table or len(table) < 3:
            return False

        # Check for dollar signs or large numbers
        financial_pattern = re.compile(r'[\$,]?\d{1,3}(,\d{3})*(\.\d{2})?')

        financial_cells = 0
        total_cells = 0

        for row in table:
            for cell in row:
                total_cells += 1
                if financial_pattern.search(str(cell)):
                    financial_cells += 1

        # If more than 30% of cells contain financial data
        if total_cells > 0:
            return (financial_cells / total_cells) > 0.3

        return False

    def extract_text_from_page(self, page_number: int) -> str:
        """Extract all text from a page"""
        if page_number < 1 or page_number > len(self.pages):
            return ""

        page = self.pages[page_number - 1]
        return page.extract_text() or ""

    def search_text(self, search_term: str, case_sensitive: bool = False) -> List[int]:
        """
        Search for text across all pages

        Args:
            search_term: Text to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of page numbers containing the search term
        """
        matching_pages = []

        for page_num, page in enumerate(self.pages, start=1):
            text = page.extract_text()
            if text:
                if not case_sensitive:
                    text = text.lower()
                    search_term = search_term.lower()

                if search_term in text:
                    matching_pages.append(page_num)

        return matching_pages

    def get_summary(self) -> Dict:
        """Get summary information about the PDF"""
        statement_pages = self.find_statement_pages()

        return {
            'filename': self.pdf_path.name,
            'total_pages': len(self.pages),
            'file_size_mb': round(self.metadata.get('file_size_mb', 0), 2),
            'has_balance_sheet': len(statement_pages['balance_sheet']) > 0,
            'has_income_statement': len(statement_pages['income_statement']) > 0,
            'has_cash_flow': len(statement_pages['cash_flow']) > 0,
            'statement_pages': statement_pages
        }


# Utility functions

def parse_financial_amount(value_str: str) -> Optional[float]:
    """
    Parse a financial amount string to float

    Args:
        value_str: String like "$1,234,567.89" or "(1,234)"

    Returns:
        Float value, or None if cannot parse
    """
    if not value_str or value_str.strip() == '':
        return None

    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[\$,\s]', '', str(value_str))

    # Handle parentheses (negative numbers)
    is_negative = '(' in value_str and ')' in value_str
    cleaned = cleaned.replace('(', '').replace(')', '')

    try:
        amount = float(cleaned)
        return -amount if is_negative else amount
    except ValueError:
        return None


def detect_table_structure(table: List[List[str]]) -> Dict:
    """
    Analyze table structure to identify headers, data rows, etc.

    Args:
        table: Table data

    Returns:
        Dictionary with structure information
    """
    if not table:
        return {}

    # Assume first row is header
    header_row = table[0]

    # Find year columns
    year_pattern = re.compile(r'\b(20\d{2})\b')
    year_columns = []

    for idx, cell in enumerate(header_row):
        if year_pattern.search(str(cell)):
            year_columns.append(idx)

    # Determine account name column (usually first column without years)
    account_column = 0
    for idx, cell in enumerate(header_row):
        if not year_pattern.search(str(cell)):
            account_column = idx
            break

    return {
        'header_row': 0,
        'account_column': account_column,
        'year_columns': year_columns,
        'data_rows': list(range(1, len(table))),
        'total_rows': len(table),
        'total_columns': len(header_row)
    }


# Example usage
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print("="*60)
    print("Financial PDF Parser")
    print("="*60)

    with FinancialPDFParser(pdf_path) as parser:
        # Get summary
        summary = parser.get_summary()

        print(f"\nFile: {summary['filename']}")
        print(f"Pages: {summary['total_pages']}")
        print(f"Size: {summary['file_size_mb']} MB")
        print(f"\nFinancial Statements Found:")
        print(f"  Balance Sheet: {'✓' if summary['has_balance_sheet'] else '✗'}")
        print(f"  Income Statement: {'✓' if summary['has_income_statement'] else '✗'}")
        print(f"  Cash Flow: {'✓' if summary['has_cash_flow'] else '✗'}")

        # Extract all statements
        print("\nExtracting tables...")
        statements = parser.extract_all_statements()

        for stmt_type, tables in statements.items():
            print(f"\n{stmt_type.upper()}:")
            print(f"  Found {len(tables)} tables")

            for table_info in tables:
                print(f"  - Page {table_info['page_number']}, "
                      f"Table {table_info['table_index']}: "
                      f"{table_info['row_count']} rows × {table_info['column_count']} cols")

                # Show first few rows
                if table_info['table_data']:
                    print(f"    First row: {table_info['table_data'][0][:3]}...")

    print("\n" + "="*60)
    print("Done!")
