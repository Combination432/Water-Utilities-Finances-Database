"""
Financial Data Extractor
Converts parsed PDF tables into structured line items
Uses rule-based matching (free, no LLM costs)
"""

import re
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialExtractor:
    """Extract structured financial data from parsed tables"""

    def __init__(self):
        # Load account matching rules
        self.account_patterns = self._load_account_patterns()

    def _load_account_patterns(self) -> Dict[str, List[Dict]]:
        """
        Load patterns for matching line item names to standardized accounts

        Returns:
            Dictionary mapping account categories to matching rules
        """
        return {
            'revenue': [
                {
                    'standardized_name': 'Operating Revenue - Water Sales',
                    'account_code': 'REV-001',
                    'patterns': [
                        r'water.*sales',
                        r'water.*service.*revenue',
                        r'revenue.*water.*sales',
                        r'charges.*water.*service'
                    ]
                },
                {
                    'standardized_name': 'Operating Revenue - Sewer Service',
                    'account_code': 'REV-002',
                    'patterns': [
                        r'sewer.*service',
                        r'wastewater.*revenue',
                        r'sewer.*charges',
                        r'revenue.*sewer'
                    ]
                },
                {
                    'standardized_name': 'Non-Operating Revenue',
                    'account_code': 'REV-004',
                    'patterns': [
                        r'investment.*income',
                        r'interest.*income',
                        r'grant.*revenue',
                        r'non[- ]operating.*revenue'
                    ]
                },
            ],

            'expense': [
                {
                    'standardized_name': 'Personnel Services',
                    'account_code': 'EXP-001',
                    'patterns': [
                        r'salaries.*wages',
                        r'personnel.*services',
                        r'labor.*costs',
                        r'employee.*compensation'
                    ]
                },
                {
                    'standardized_name': 'Contractual Services',
                    'account_code': 'EXP-002',
                    'patterns': [
                        r'contractual.*services',
                        r'professional.*services',
                        r'consultant.*fees'
                    ]
                },
                {
                    'standardized_name': 'Utilities and Fuel',
                    'account_code': 'EXP-003',
                    'patterns': [
                        r'utilities.*fuel',
                        r'energy.*costs',
                        r'power.*costs',
                        r'electric.*expense'
                    ]
                },
                {
                    'standardized_name': 'Repairs and Maintenance',
                    'account_code': 'EXP-004',
                    'patterns': [
                        r'repairs.*maintenance',
                        r'maintenance.*expense',
                        r'repair.*expense'
                    ]
                },
                {
                    'standardized_name': 'Depreciation and Amortization',
                    'account_code': 'EXP-005',
                    'patterns': [
                        r'depreciation',
                        r'amortization',
                        r'depreciation.*amortization'
                    ]
                },
                {
                    'standardized_name': 'Interest Expense',
                    'account_code': 'EXP-006',
                    'patterns': [
                        r'interest.*expense',
                        r'interest.*debt',
                        r'debt.*service.*interest'
                    ]
                },
            ],

            'asset': [
                {
                    'standardized_name': 'Cash and Cash Equivalents',
                    'account_code': 'AST-001',
                    'patterns': [
                        r'^cash$',
                        r'cash.*equivalents',
                        r'cash.*cash.*equivalents'
                    ]
                },
                {
                    'standardized_name': 'Investments',
                    'account_code': 'AST-002',
                    'patterns': [
                        r'investments',
                        r'investment.*securities'
                    ]
                },
                {
                    'standardized_name': 'Accounts Receivable',
                    'account_code': 'AST-003',
                    'patterns': [
                        r'accounts.*receivable',
                        r'receivables',
                        r'customer.*receivables'
                    ]
                },
                {
                    'standardized_name': 'Capital Assets - Infrastructure',
                    'account_code': 'AST-004',
                    'patterns': [
                        r'infrastructure',
                        r'water.*system',
                        r'sewer.*system',
                        r'capital.*assets.*infrastructure'
                    ]
                },
                {
                    'standardized_name': 'Accumulated Depreciation',
                    'account_code': 'AST-007',
                    'patterns': [
                        r'accumulated.*depreciation',
                        r'less.*accumulated.*depreciation'
                    ]
                },
            ],

            'liability': [
                {
                    'standardized_name': 'Accounts Payable',
                    'account_code': 'LIA-001',
                    'patterns': [
                        r'accounts.*payable',
                        r'payables'
                    ]
                },
                {
                    'standardized_name': 'Current Portion of Long-Term Debt',
                    'account_code': 'LIA-003',
                    'patterns': [
                        r'current.*portion.*debt',
                        r'current.*debt',
                        r'short[- ]term.*debt'
                    ]
                },
                {
                    'standardized_name': 'Bonds Payable',
                    'account_code': 'LIA-004',
                    'patterns': [
                        r'bonds.*payable',
                        r'revenue.*bonds',
                        r'long[- ]term.*debt',
                        r'municipal.*bonds'
                    ]
                },
            ],

            'equity': [
                {
                    'standardized_name': 'Net Investment in Capital Assets',
                    'account_code': 'EQT-001',
                    'patterns': [
                        r'net.*investment.*capital',
                        r'invested.*capital.*assets'
                    ]
                },
                {
                    'standardized_name': 'Restricted Net Position',
                    'account_code': 'EQT-002',
                    'patterns': [
                        r'restricted.*net.*position',
                        r'restricted.*assets',
                        r'restricted.*funds'
                    ]
                },
                {
                    'standardized_name': 'Unrestricted Net Position',
                    'account_code': 'EQT-003',
                    'patterns': [
                        r'unrestricted.*net.*position',
                        r'unrestricted'
                    ]
                },
            ]
        }

    def extract_line_items(
        self,
        table_data: List[List[str]],
        statement_type: str,
        fiscal_year: int
    ) -> List[Dict]:
        """
        Extract line items from a table

        Args:
            table_data: Parsed table (list of rows)
            statement_type: 'balance_sheet', 'income_statement', or 'cash_flow'
            fiscal_year: Fiscal year for this data

        Returns:
            List of line item dictionaries
        """
        if not table_data or len(table_data) < 2:
            logger.warning("Table too small to extract data")
            return []

        # Identify structure
        structure = self._detect_table_structure(table_data)

        if not structure:
            logger.warning("Could not detect table structure")
            return []

        # Extract items
        line_items = []

        account_col = structure['account_column']
        year_col = structure.get('year_column', 1)  # Default to column 1

        for row_idx in range(structure['data_start_row'], len(table_data)):
            row = table_data[row_idx]

            if len(row) <= max(account_col, year_col):
                continue

            account_name = row[account_col].strip()
            amount_str = row[year_col].strip()

            # Skip empty or header rows
            if not account_name or not amount_str:
                continue

            # Skip subtotal/total rows (we'll calculate these)
            if self._is_total_row(account_name):
                continue

            # Parse amount
            amount = self._parse_amount(amount_str)

            if amount is None:
                continue

            # Determine category and match to standardized account
            category = self._determine_category(statement_type, account_name)
            standardized = self._match_standardized_account(account_name, category)

            # Create line item
            line_item = {
                'line_item_name': account_name,
                'amount': amount,
                'fiscal_year': fiscal_year,
                'line_item_category': category,
                'statement_type': statement_type,
                'standardized_account_name': standardized['name'] if standardized else None,
                'account_code': standardized['code'] if standardized else None,
                'confidence_score': standardized['confidence'] if standardized else 0.5,
            }

            line_items.append(line_item)

        logger.info(f"Extracted {len(line_items)} line items from table")
        return line_items

    def _detect_table_structure(self, table: List[List[str]]) -> Optional[Dict]:
        """
        Detect table structure (columns for account names, amounts, years)

        Args:
            table: Table data

        Returns:
            Dictionary with structure information
        """
        if len(table) < 2:
            return None

        header_row = table[0]

        # Find year columns
        year_pattern = re.compile(r'\b(20\d{2})\b')
        year_columns = {}

        for idx, cell in enumerate(header_row):
            years = year_pattern.findall(str(cell))
            if years:
                year_columns[idx] = int(years[0])

        if not year_columns:
            # Assume column 1 is the amount column if no years found
            year_columns = {1: None}

        # Account name column is usually column 0
        account_column = 0

        # Data starts on row 1 (after header)
        data_start_row = 1

        return {
            'account_column': account_column,
            'year_columns': year_columns,
            'year_column': list(year_columns.keys())[0],  # Use first year column
            'data_start_row': data_start_row,
        }

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse financial amount from string

        Args:
            amount_str: String like "$1,234,567.89" or "(1,234)"

        Returns:
            Float value or None
        """
        if not amount_str or amount_str.strip() in ['', '-', '—']:
            return None

        # Remove currency symbols, commas, and whitespace
        cleaned = re.sub(r'[\$,\s]', '', amount_str)

        # Handle parentheses (negative numbers)
        is_negative = '(' in amount_str and ')' in amount_str
        cleaned = cleaned.replace('(', '').replace(')', '')

        # Handle dashes (sometimes used for zero)
        if cleaned in ['-', '—', '–']:
            return 0.0

        try:
            amount = float(cleaned)
            return -amount if is_negative else amount
        except ValueError:
            return None

    def _is_total_row(self, account_name: str) -> bool:
        """Check if row is a subtotal or total"""
        account_lower = account_name.lower()
        total_keywords = [
            'total', 'subtotal', 'net income', 'net position',
            'total assets', 'total liabilities', 'total revenue',
            'total expense', 'total operating'
        ]
        return any(keyword in account_lower for keyword in total_keywords)

    def _determine_category(self, statement_type: str, account_name: str) -> str:
        """
        Determine line item category based on statement type and account name

        Args:
            statement_type: Type of statement
            account_name: Name of account

        Returns:
            Category string
        """
        account_lower = account_name.lower()

        if statement_type == 'balance_sheet':
            # Determine if asset, liability, or equity
            if any(word in account_lower for word in ['asset', 'cash', 'receivable', 'investment', 'property', 'equipment', 'infrastructure']):
                return 'asset'
            elif any(word in account_lower for word in ['liability', 'payable', 'debt', 'bond', 'obligation']):
                return 'liability'
            elif any(word in account_lower for word in ['equity', 'net position', 'fund balance', 'retained earnings']):
                return 'equity'
            else:
                return 'unknown'

        elif statement_type == 'income_statement':
            # Determine if revenue or expense
            if any(word in account_lower for word in ['revenue', 'sales', 'income', 'charges']):
                return 'revenue'
            elif any(word in account_lower for word in ['expense', 'cost', 'depreciation', 'amortization', 'interest expense', 'loss']):
                return 'expense'
            else:
                return 'unknown'

        elif statement_type == 'cash_flow':
            return 'cash_flow'

        return 'unknown'

    def _match_standardized_account(
        self,
        account_name: str,
        category: str
    ) -> Optional[Dict]:
        """
        Match account name to standardized account

        Args:
            account_name: Raw account name from statement
            category: Category (revenue, expense, etc.)

        Returns:
            Dictionary with matched account info and confidence score
        """
        if category not in self.account_patterns:
            return None

        account_lower = account_name.lower()
        best_match = None
        best_score = 0.0

        for account_info in self.account_patterns[category]:
            score = 0.0

            # Check each pattern
            for pattern in account_info['patterns']:
                if re.search(pattern, account_lower):
                    score = 1.0
                    break

            # Fuzzy matching (simple word overlap)
            if score == 0:
                account_words = set(re.findall(r'\w+', account_lower))
                pattern_words = set(re.findall(r'\w+', ' '.join(account_info['patterns']).lower()))
                overlap = len(account_words & pattern_words)
                score = overlap / max(len(account_words), len(pattern_words)) if pattern_words else 0

            if score > best_score:
                best_score = score
                best_match = account_info

        if best_match and best_score > 0.3:  # Minimum threshold
            return {
                'name': best_match['standardized_name'],
                'code': best_match['account_code'],
                'confidence': best_score
            }

        return None

    def validate_extraction(self, line_items: List[Dict], statement_type: str) -> Dict:
        """
        Validate extracted line items

        Args:
            line_items: List of extracted line items
            statement_type: Type of statement

        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }

        if not line_items:
            validation['errors'].append("No line items extracted")
            validation['is_valid'] = False
            return validation

        # Check for balance sheet equation (Assets = Liabilities + Equity)
        if statement_type == 'balance_sheet':
            total_assets = sum(item['amount'] for item in line_items if item['line_item_category'] == 'asset')
            total_liabilities = sum(item['amount'] for item in line_items if item['line_item_category'] == 'liability')
            total_equity = sum(item['amount'] for item in line_items if item['line_item_category'] == 'equity')

            if total_assets > 0 and total_liabilities > 0:
                diff = abs(total_assets - (total_liabilities + total_equity))
                diff_pct = diff / total_assets * 100

                if diff_pct > 5:  # More than 5% difference
                    validation['warnings'].append(
                        f"Balance sheet equation doesn't balance: Assets={total_assets:,.0f}, "
                        f"Liabilities+Equity={total_liabilities + total_equity:,.0f} "
                        f"(Diff: {diff_pct:.1f}%)"
                    )

        # Check for low confidence matches
        low_confidence = [item for item in line_items if item.get('confidence_score', 0) < 0.5]
        if low_confidence:
            validation['warnings'].append(
                f"{len(low_confidence)} line items have low confidence matches"
            )

        # Check for unmapped items
        unmapped = [item for item in line_items if not item.get('standardized_account_name')]
        if unmapped:
            validation['warnings'].append(
                f"{len(unmapped)} line items could not be mapped to standardized accounts"
            )

        return validation


# Example usage
if __name__ == '__main__':
    # Sample table data
    sample_table = [
        ['Account', '2023', '2022'],
        ['Water Sales Revenue', '5,234,567', '4,987,123'],
        ['Sewer Service Charges', '2,456,789', '2,345,678'],
        ['Personnel Services', '(1,234,567)', '(1,123,456)'],
        ['Depreciation', '(876,543)', '(823,456)'],
    ]

    print("="*60)
    print("Financial Data Extractor Test")
    print("="*60)

    extractor = FinancialExtractor()

    # Extract line items
    line_items = extractor.extract_line_items(
        sample_table,
        statement_type='income_statement',
        fiscal_year=2023
    )

    print(f"\nExtracted {len(line_items)} line items:\n")

    for item in line_items:
        print(f"  {item['line_item_name']}")
        print(f"    Amount: ${item['amount']:,.2f}")
        print(f"    Category: {item['line_item_category']}")
        print(f"    Standardized: {item['standardized_account_name'] or 'N/A'}")
        print(f"    Confidence: {item.get('confidence_score', 0):.2f}")
        print()

    # Validate
    validation = extractor.validate_extraction(line_items, 'income_statement')

    print("Validation:")
    print(f"  Valid: {validation['is_valid']}")
    if validation['warnings']:
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    - {warning}")
