"""
Database Setup and Connection Module
Handles PostgreSQL database initialization and connections
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration - modify these for your setup"""

    def __init__(self):
        # Default to local PostgreSQL
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME', 'water_utilities')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'postgres')

    def get_connection_string(self, database: Optional[str] = None) -> str:
        """Get PostgreSQL connection string"""
        db = database or self.database
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{db}"

    def get_connection_params(self, database: Optional[str] = None) -> dict:
        """Get connection parameters as dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'database': database or self.database,
            'user': self.user,
            'password': self.password
        }


def create_database(config: DatabaseConfig):
    """Create the database if it doesn't exist"""
    try:
        # Connect to postgres database to create our database
        conn = psycopg2.connect(**config.get_connection_params('postgres'))
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.database,)
        )

        if cursor.fetchone():
            logger.info(f"Database '{config.database}' already exists")
        else:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(config.database)
                )
            )
            logger.info(f"✓ Created database '{config.database}'")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def initialize_schema(config: DatabaseConfig):
    """Initialize database schema from SQL file"""
    try:
        # Connect to our database
        conn = psycopg2.connect(**config.get_connection_params())
        cursor = conn.cursor()

        # Read schema file
        schema_file = Path(__file__).parent / 'schema.sql'
        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Execute schema
        logger.info("Executing schema.sql...")
        cursor.execute(schema_sql)
        conn.commit()

        logger.info("✓ Database schema initialized successfully")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error initializing schema: {e}")
        return False
    except FileNotFoundError:
        logger.error("schema.sql file not found")
        return False


def get_connection(config: Optional[DatabaseConfig] = None):
    """Get a database connection"""
    if config is None:
        config = DatabaseConfig()

    try:
        conn = psycopg2.connect(**config.get_connection_params())
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def test_connection(config: Optional[DatabaseConfig] = None) -> bool:
    """Test database connection"""
    if config is None:
        config = DatabaseConfig()

    try:
        conn = get_connection(config)
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        logger.info("✓ Database connection successful")
        logger.info(f"  PostgreSQL version: {version}")

        # Check tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()
        logger.info(f"  Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"    - {table[0]}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def get_statistics(config: Optional[DatabaseConfig] = None) -> dict:
    """Get database statistics"""
    if config is None:
        config = DatabaseConfig()

    try:
        conn = get_connection(config)
        cursor = conn.cursor()

        stats = {}

        # Count utilities
        cursor.execute("SELECT COUNT(*) FROM utilities;")
        stats['utilities'] = cursor.fetchone()[0]

        # Count reports
        cursor.execute("SELECT COUNT(*) FROM financial_reports;")
        stats['reports'] = cursor.fetchone()[0]

        # Count line items
        cursor.execute("SELECT COUNT(*) FROM line_items;")
        stats['line_items'] = cursor.fetchone()[0]

        # Count statements
        cursor.execute("SELECT COUNT(*) FROM financial_statements;")
        stats['statements'] = cursor.fetchone()[0]

        # Reports by status
        cursor.execute("""
            SELECT processing_status, COUNT(*)
            FROM financial_reports
            GROUP BY processing_status;
        """)
        stats['reports_by_status'] = dict(cursor.fetchall())

        # Year coverage
        cursor.execute("""
            SELECT MIN(fiscal_year) as earliest,
                   MAX(fiscal_year) as latest,
                   COUNT(DISTINCT fiscal_year) as years
            FROM financial_reports
            WHERE processing_status = 'completed';
        """)
        row = cursor.fetchone()
        if row[0]:
            stats['year_coverage'] = {
                'earliest': row[0],
                'latest': row[1],
                'total_years': row[2]
            }

        cursor.close()
        conn.close()
        return stats

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {}


def reset_database(config: Optional[DatabaseConfig] = None):
    """
    DANGER: Drop and recreate database
    Use only for development/testing
    """
    if config is None:
        config = DatabaseConfig()

    try:
        # Connect to postgres database
        conn = psycopg2.connect(**config.get_connection_params('postgres'))
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        logger.warning(f"⚠️  Dropping database '{config.database}'...")

        # Terminate existing connections
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{config.database}'
              AND pid <> pg_backend_pid();
        """)

        # Drop database
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(config.database)
            )
        )

        logger.info("✓ Database dropped")

        cursor.close()
        conn.close()

        # Recreate
        create_database(config)
        initialize_schema(config)

        logger.info("✓ Database reset complete")
        return True

    except psycopg2.Error as e:
        logger.error(f"Error resetting database: {e}")
        return False


def main():
    """Setup database from command line"""
    import argparse

    parser = argparse.ArgumentParser(description='Water Utilities Database Setup')
    parser.add_argument('command', choices=['create', 'init', 'test', 'stats', 'reset'],
                        help='Command to execute')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default='5432', help='Database port')
    parser.add_argument('--database', default='water_utilities', help='Database name')
    parser.add_argument('--user', default='postgres', help='Database user')
    parser.add_argument('--password', default='postgres', help='Database password')

    args = parser.parse_args()

    # Create config from args
    config = DatabaseConfig()
    config.host = args.host
    config.port = args.port
    config.database = args.database
    config.user = args.user
    config.password = args.password

    print(f"\n{'='*60}")
    print(f"Water Utilities Database Setup")
    print(f"{'='*60}")
    print(f"Host: {config.host}:{config.port}")
    print(f"Database: {config.database}")
    print(f"User: {config.user}")
    print(f"{'='*60}\n")

    if args.command == 'create':
        create_database(config)

    elif args.command == 'init':
        create_database(config)
        initialize_schema(config)

    elif args.command == 'test':
        test_connection(config)

    elif args.command == 'stats':
        stats = get_statistics(config)
        print("\nDatabase Statistics:")
        print(f"{'='*60}")
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")

    elif args.command == 'reset':
        response = input("⚠️  This will DELETE ALL DATA. Are you sure? (type 'yes'): ")
        if response.lower() == 'yes':
            reset_database(config)
        else:
            print("Cancelled")

    print()


if __name__ == '__main__':
    main()
