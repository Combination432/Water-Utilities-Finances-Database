"""
Pipeline Orchestrator
Coordinates the complete data collection and processing pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.db_setup import DatabaseConfig, get_connection
from emma-pipeline.emma_scraper import EmmaScraper, RateLimiter
from parsers.pdf_parser import FinancialPDFParser
from extractors.financial_extractor import FinancialExtractor
import logging
import time
from datetime import datetime
from pathlib import Path
import hashlib
import uuid
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the complete data pipeline"""

    def __init__(self, db_config=None, data_dir="./data"):
        """
        Initialize orchestrator

        Args:
            db_config: DatabaseConfig instance
            data_dir: Directory for storing PDFs
        """
        self.config = db_config or DatabaseConfig()
        self.conn = get_connection(self.config)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.data_dir / "pdfs").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)

        self.scraper = EmmaScraper()
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        self.extractor = FinancialExtractor()

        self.stats = {
            'utilities_discovered': 0,
            'documents_found': 0,
            'documents_downloaded': 0,
            'documents_parsed': 0,
            'line_items_extracted': 0,
            'errors': []
        }

    def discover_utilities(self, states=None, search_term="water"):
        """
        Stage 1: Discover utilities from EMMA

        Args:
            states: List of state codes (e.g., ['CA', 'TX'])
            search_term: Search term for utilities

        Returns:
            List of discovered utilities
        """
        logger.info("="*60)
        logger.info("STAGE 1: DISCOVERY - Finding utilities from EMMA")
        logger.info("="*60)

        if states is None:
            states = self._get_top_states()

        all_utilities = {}

        for state in states:
            logger.info(f"\nSearching {state}...")
            self.rate_limiter.wait_if_needed()

            try:
                # Search EMMA for issuers
                issuers = self.scraper.search_issuers(
                    issuer_name=search_term,
                    state=state,
                    max_results=50
                )

                logger.info(f"  Found {len(issuers)} issuers in {state}")

                for issuer in issuers:
                    key = f"{issuer['name']}_{state}"

                    if key not in all_utilities:
                        all_utilities[key] = {
                            'name': issuer['name'],
                            'state': state,
                            'emma_issuer_id': issuer.get('emma_issuer_id'),
                            'source': 'emma'
                        }

                        # Store in database
                        self._store_utility(all_utilities[key])

                self.stats['utilities_discovered'] += len(issuers)

            except Exception as e:
                logger.error(f"Error searching {state}: {e}")
                self.stats['errors'].append(f"Discovery {state}: {str(e)}")

        logger.info(f"\n✓ Discovery complete: {len(all_utilities)} utilities found")
        return list(all_utilities.values())

    def discover_documents(self, utility_id, utility_name, state, years=None):
        """
        Stage 2: Discover financial documents for a utility

        Args:
            utility_id: UUID of utility
            utility_name: Name of utility
            state: State code
            years: List of years to find (default: last 10 years)

        Returns:
            List of discovered documents
        """
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 10, current_year))

        logger.info(f"Searching documents for {utility_name}...")
        self.rate_limiter.wait_if_needed()

        try:
            documents = self.scraper.search_documents(
                issuer_name=utility_name,
                state=state,
                document_type="Annual Financial Information",
                years=years
            )

            logger.info(f"  Found {len(documents)} documents")

            # Store in database
            for doc in documents:
                self._store_financial_report(utility_id, doc)

            self.stats['documents_found'] += len(documents)
            return documents

        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            self.stats['errors'].append(f"Documents {utility_name}: {str(e)}")
            return []

    def download_document(self, report_id, document_id, utility_id):
        """
        Stage 3: Download PDF document

        Args:
            report_id: UUID of financial report
            document_id: EMMA document ID
            utility_id: UUID of utility

        Returns:
            Path to downloaded file or None
        """
        # Create directory for this utility
        utility_dir = self.data_dir / "pdfs" / str(utility_id)
        utility_dir.mkdir(exist_ok=True)

        # Download path
        file_path = utility_dir / f"{document_id}.pdf"

        # Skip if already downloaded
        if file_path.exists():
            logger.info(f"  Already downloaded: {document_id}")
            return str(file_path)

        # Update status
        self._update_report_status(report_id, 'downloading')

        # Download
        self.rate_limiter.wait_if_needed()

        try:
            success = self.scraper.download_document(document_id, str(file_path))

            if success:
                # Calculate hash
                file_hash = self._calculate_file_hash(file_path)

                # Update database
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE financial_reports
                    SET document_storage_path = %s,
                        file_hash = %s,
                        file_size_bytes = %s,
                        processing_status = 'downloaded'
                    WHERE report_id = %s
                """, (str(file_path), file_hash, file_path.stat().st_size, report_id))
                self.conn.commit()
                cursor.close()

                self.stats['documents_downloaded'] += 1
                return str(file_path)
            else:
                self._update_report_status(report_id, 'failed', 'Download failed')
                return None

        except Exception as e:
            logger.error(f"Error downloading {document_id}: {e}")
            self._update_report_status(report_id, 'failed', str(e))
            self.stats['errors'].append(f"Download {document_id}: {str(e)}")
            return None

    def parse_and_extract(self, report_id, pdf_path, utility_id, fiscal_year):
        """
        Stage 4 & 5: Parse PDF and extract financial data

        Args:
            report_id: UUID of financial report
            pdf_path: Path to PDF file
            utility_id: UUID of utility
            fiscal_year: Fiscal year

        Returns:
            Number of line items extracted
        """
        logger.info(f"  Parsing PDF: {Path(pdf_path).name}")

        # Update status
        self._update_report_status(report_id, 'parsing')

        try:
            # Parse PDF
            with FinancialPDFParser(pdf_path) as parser:
                # Extract all statements
                statements = parser.extract_all_statements()

                if not statements:
                    logger.warning("    No financial statements found in PDF")
                    self._update_report_status(report_id, 'completed', 'No statements found')
                    return 0

                # Update report flags
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE financial_reports
                    SET has_balance_sheet = %s,
                        has_income_statement = %s,
                        has_cash_flow = %s,
                        processing_status = 'extracting'
                    WHERE report_id = %s
                """, (
                    'balance_sheet' in statements,
                    'income_statement' in statements,
                    'cash_flow' in statements,
                    report_id
                ))
                self.conn.commit()

                total_line_items = 0

                # Process each statement
                for stmt_type, tables in statements.items():
                    logger.info(f"    Processing {stmt_type}...")

                    # Create statement record
                    statement_id = self._create_statement_record(
                        report_id, utility_id, stmt_type, fiscal_year
                    )

                    # Extract from each table
                    for table_info in tables:
                        line_items = self.extractor.extract_line_items(
                            table_data=table_info['table_data'],
                            statement_type=stmt_type,
                            fiscal_year=fiscal_year
                        )

                        # Store line items
                        for item in line_items:
                            self._store_line_item(statement_id, utility_id, item)

                        total_line_items += len(line_items)

                self.conn.commit()
                cursor.close()

                logger.info(f"    ✓ Extracted {total_line_items} line items")

                # Update final status
                self._update_report_status(report_id, 'completed')

                self.stats['documents_parsed'] += 1
                self.stats['line_items_extracted'] += total_line_items

                return total_line_items

        except Exception as e:
            logger.error(f"    Error parsing/extracting: {e}")
            self._update_report_status(report_id, 'failed', str(e))
            self.stats['errors'].append(f"Parse {Path(pdf_path).name}: {str(e)}")
            return 0

    def process_utility(self, utility_id, utility_name, state, years=10):
        """
        Process complete pipeline for one utility

        Args:
            utility_id: UUID of utility
            utility_name: Name of utility
            state: State code
            years: Number of years to collect

        Returns:
            Statistics dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING: {utility_name} ({state})")
        logger.info(f"{'='*60}")

        stats = {
            'documents_found': 0,
            'documents_downloaded': 0,
            'documents_parsed': 0,
            'line_items_extracted': 0
        }

        # Discover documents
        current_year = datetime.now().year
        year_list = list(range(current_year - years, current_year))

        documents = self.discover_documents(utility_id, utility_name, state, year_list)
        stats['documents_found'] = len(documents)

        # Process each document
        for doc in documents:
            # Get report record
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT report_id, emma_document_id, fiscal_year, processing_status
                FROM financial_reports
                WHERE utility_id = %s AND fiscal_year = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (utility_id, doc.get('fiscal_year')))

            result = cursor.fetchone()
            cursor.close()

            if not result:
                continue

            report_id, emma_doc_id, fiscal_year, status = result

            # Skip if already completed
            if status == 'completed':
                logger.info(f"  Skipping FY{fiscal_year} (already completed)")
                continue

            # Download
            pdf_path = self.download_document(report_id, emma_doc_id, utility_id)

            if pdf_path:
                stats['documents_downloaded'] += 1

                # Parse and extract
                line_items = self.parse_and_extract(report_id, pdf_path, utility_id, fiscal_year)

                if line_items > 0:
                    stats['documents_parsed'] += 1
                    stats['line_items_extracted'] += line_items

        return stats

    def process_batch(self, utilities, max_utilities=None):
        """
        Process a batch of utilities

        Args:
            utilities: List of utility dictionaries
            max_utilities: Maximum number to process (None = all)

        Returns:
            Batch statistics
        """
        logger.info("\n" + "🔄"*30)
        logger.info(" "*15 + "BATCH PROCESSING PIPELINE")
        logger.info("🔄"*30)

        batch_stats = {
            'total_utilities': 0,
            'successful': 0,
            'failed': 0,
            'documents_collected': 0,
            'line_items_extracted': 0
        }

        utilities_to_process = utilities[:max_utilities] if max_utilities else utilities

        for i, utility in enumerate(utilities_to_process, 1):
            logger.info(f"\n[{i}/{len(utilities_to_process)}]")

            try:
                # Get utility_id from database
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT utility_id FROM utilities
                    WHERE name = %s AND state_code = %s
                """, (utility['name'], utility['state']))

                result = cursor.fetchone()
                cursor.close()

                if not result:
                    logger.warning(f"  Utility not found in database: {utility['name']}")
                    continue

                utility_id = result[0]

                # Process
                stats = self.process_utility(
                    utility_id=utility_id,
                    utility_name=utility['name'],
                    state=utility['state'],
                    years=10
                )

                batch_stats['total_utilities'] += 1
                batch_stats['successful'] += 1
                batch_stats['documents_collected'] += stats['documents_parsed']
                batch_stats['line_items_extracted'] += stats['line_items_extracted']

            except Exception as e:
                logger.error(f"  Failed to process {utility['name']}: {e}")
                batch_stats['failed'] += 1

        return batch_stats

    # Helper methods

    def _get_top_states(self):
        """Get top 10 states by population"""
        return ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']

    def _store_utility(self, utility_data):
        """Store utility in database"""
        cursor = self.conn.cursor()

        try:
            utility_id = str(uuid.uuid4())

            cursor.execute("""
                INSERT INTO utilities (
                    utility_id, name, state_code, emma_issuer_id, utility_type
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name, state_code) DO NOTHING
                RETURNING utility_id
            """, (
                utility_id,
                utility_data['name'],
                utility_data['state'],
                utility_data.get('emma_issuer_id'),
                'special_district'  # Default for EMMA issuers
            ))

            self.conn.commit()

        except Exception as e:
            logger.debug(f"Error storing utility: {e}")
            self.conn.rollback()

        finally:
            cursor.close()

    def _store_financial_report(self, utility_id, document):
        """Store financial report record"""
        cursor = self.conn.cursor()

        try:
            report_id = str(uuid.uuid4())

            cursor.execute("""
                INSERT INTO financial_reports (
                    report_id, utility_id, fiscal_year, fiscal_year_end_date,
                    report_type, report_title, emma_document_id,
                    document_url, processing_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (utility_id, fiscal_year, report_type) DO NOTHING
            """, (
                report_id, utility_id,
                document.get('fiscal_year'),
                document.get('fiscal_year_end_date', f"{document.get('fiscal_year')}-06-30"),
                document.get('document_type', 'CAFR'),
                document.get('title'),
                document.get('document_id'),
                document.get('document_url'),
                'pending'
            ))

            self.conn.commit()

        except Exception as e:
            logger.debug(f"Error storing report: {e}")
            self.conn.rollback()

        finally:
            cursor.close()

    def _update_report_status(self, report_id, status, error_message=None):
        """Update report processing status"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                UPDATE financial_reports
                SET processing_status = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE report_id = %s
            """, (status, error_message, report_id))

            self.conn.commit()

        finally:
            cursor.close()

    def _create_statement_record(self, report_id, utility_id, statement_type, fiscal_year):
        """Create financial statement record"""
        cursor = self.conn.cursor()

        statement_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO financial_statements (
                statement_id, report_id, utility_id, statement_type,
                fiscal_year, period_start_date, period_end_date,
                extraction_method
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING statement_id
        """, (
            statement_id, report_id, utility_id, statement_type,
            fiscal_year,
            f"{fiscal_year-1}-07-01",
            f"{fiscal_year}-06-30",
            'rule_based'
        ))

        self.conn.commit()
        cursor.close()

        return statement_id

    def _store_line_item(self, statement_id, utility_id, line_item_data):
        """Store a line item"""
        cursor = self.conn.cursor()

        # Get standardized account ID if available
        std_account_id = None
        if line_item_data.get('account_code'):
            cursor.execute("""
                SELECT account_id FROM standardized_accounts
                WHERE account_code = %s
            """, (line_item_data['account_code'],))
            result = cursor.fetchone()
            if result:
                std_account_id = result[0]

        cursor.execute("""
            INSERT INTO line_items (
                line_item_id, statement_id, utility_id, fiscal_year,
                line_item_name, line_item_category, amount,
                standardized_account_id, standardized_account_name,
                account_code, confidence_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            statement_id,
            utility_id,
            line_item_data['fiscal_year'],
            line_item_data['line_item_name'],
            line_item_data['line_item_category'],
            line_item_data['amount'],
            std_account_id,
            line_item_data.get('standardized_account_name'),
            line_item_data.get('account_code'),
            line_item_data.get('confidence_score', 0.5)
        ))

        cursor.close()

    def _calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def print_stats(self):
        """Print pipeline statistics"""
        print("\n" + "="*60)
        print("PIPELINE STATISTICS")
        print("="*60)
        for key, value in self.stats.items():
            if key != 'errors':
                print(f"{key}: {value}")

        if self.stats['errors']:
            print(f"\nErrors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"  - {error}")

        print("="*60)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Run pipeline from command line"""
    import argparse

    parser = argparse.ArgumentParser(description='Water Utilities Data Pipeline')
    parser.add_argument('--discover', action='store_true', help='Discover utilities from EMMA')
    parser.add_argument('--states', nargs='+', help='States to search (e.g., CA TX FL)')
    parser.add_argument('--max-utilities', type=int, help='Maximum utilities to process')
    parser.add_argument('--data-dir', default='./data', help='Directory for PDFs')

    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(data_dir=args.data_dir)

    try:
        if args.discover:
            # Discover utilities
            utilities = orchestrator.discover_utilities(states=args.states)

            # Process batch
            batch_stats = orchestrator.process_batch(utilities, max_utilities=args.max_utilities)

            print("\n" + "="*60)
            print("BATCH RESULTS")
            print("="*60)
            for key, value in batch_stats.items():
                print(f"{key}: {value}")
            print("="*60)

        orchestrator.print_stats()

    finally:
        orchestrator.close()


if __name__ == '__main__':
    main()
