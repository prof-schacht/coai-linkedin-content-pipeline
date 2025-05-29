#!/usr/bin/env python3
"""
Import LinkedIn connections from CSV export.
Handles privacy protection by hashing emails.
"""

import os
import sys
import csv
import hashlib
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import init_db, get_db
from src.models.linkedin_connection import LinkedInConnection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def hash_email(email: str) -> str:
    """Create SHA256 hash of email for privacy protection."""
    if not email:
        return ""
    # Normalize email
    email = email.strip().lower()
    # Create hash
    return hashlib.sha256(email.encode()).hexdigest()


def parse_connection_date(date_str: str) -> datetime:
    """Parse LinkedIn connection date format."""
    if not date_str:
        return None
    
    # LinkedIn uses format like "15 Jan 2023"
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y")
    except:
        # Try alternative formats
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except:
            logger.warning(f"Could not parse date: {date_str}")
            return None


def import_connections(csv_path: str, exclude_file: str = None) -> dict:
    """
    Import connections from LinkedIn CSV export.
    
    Args:
        csv_path: Path to LinkedIn connections CSV
        exclude_file: Optional file with emails to exclude
        
    Returns:
        Import statistics
    """
    stats = {
        "total_rows": 0,
        "imported": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0
    }
    
    # Load exclusion list
    excluded_emails = set()
    if exclude_file and os.path.exists(exclude_file):
        with open(exclude_file, 'r') as f:
            excluded_emails = {line.strip().lower() for line in f}
        logger.info(f"Loaded {len(excluded_emails)} emails to exclude")
    
    # Expected CSV columns from LinkedIn export
    expected_columns = {
        'First Name': 'first_name',
        'Last Name': 'last_name', 
        'Email Address': 'email',
        'Company': 'company',
        'Position': 'position',
        'Connected On': 'connected_on'
    }
    
    with get_db() as db:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row in reader:
                stats["total_rows"] += 1
                
                try:
                    # Extract data
                    email = row.get('Email Address', '').strip()
                    
                    # Skip if excluded
                    if email.lower() in excluded_emails:
                        stats["skipped"] += 1
                        continue
                    
                    # Skip if no email (privacy)
                    if not email:
                        stats["skipped"] += 1
                        continue
                    
                    # Create connection hash
                    connection_hash = hash_email(email)
                    
                    # Build full name
                    first_name = row.get('First Name', '').strip()
                    last_name = row.get('Last Name', '').strip()
                    full_name = f"{first_name} {last_name}".strip()
                    
                    if not full_name:
                        stats["skipped"] += 1
                        continue
                    
                    # Extract other fields
                    company = row.get('Company', '').strip()
                    position = row.get('Position', '').strip()
                    connected_date = parse_connection_date(row.get('Connected On', ''))
                    
                    # Check if connection exists
                    existing = db.query(LinkedInConnection).filter_by(
                        connection_hash=connection_hash
                    ).first()
                    
                    if existing:
                        # Update existing
                        existing.full_name = full_name
                        existing.company = company
                        existing.position = position
                        if connected_date:
                            existing.connected_date = connected_date.date()
                        existing.updated_at = datetime.utcnow()
                        stats["updated"] += 1
                    else:
                        # Create new
                        connection = LinkedInConnection(
                            connection_hash=connection_hash,
                            full_name=full_name,
                            company=company,
                            position=position,
                            connected_date=connected_date.date() if connected_date else None
                        )
                        db.add(connection)
                        stats["imported"] += 1
                    
                    # Commit every 100 records
                    if (stats["imported"] + stats["updated"]) % 100 == 0:
                        db.commit()
                        logger.info(f"Progress: {stats['imported']} imported, {stats['updated']} updated")
                
                except Exception as e:
                    logger.error(f"Error processing row {stats['total_rows']}: {e}")
                    stats["errors"] += 1
            
            # Final commit
            db.commit()
    
    return stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Import LinkedIn connections from CSV export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  python scripts/import_connections.py connections.csv
  
  # Import with exclusions
  python scripts/import_connections.py connections.csv --exclude exclude.txt
  
  # Dry run to check format
  python scripts/import_connections.py connections.csv --dry-run

How to export from LinkedIn:
  1. Go to https://www.linkedin.com/mypreferences/d/download-my-data
  2. Select "Connections" 
  3. Request archive
  4. Download and extract the CSV file
        """
    )
    
    parser.add_argument(
        "csv_file",
        help="Path to LinkedIn connections CSV file"
    )
    parser.add_argument(
        "--exclude",
        help="File containing emails to exclude (one per line)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate CSV format without importing"
    )
    
    args = parser.parse_args()
    
    # Check file exists
    if not os.path.exists(args.csv_file):
        logger.error(f"File not found: {args.csv_file}")
        return 1
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1
    
    if args.dry_run:
        # Just validate format
        with open(args.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            print("CSV Headers found:")
            for header in headers:
                print(f"  - {header}")
            
            print("\nExpected headers:")
            print("  - First Name")
            print("  - Last Name")
            print("  - Email Address")
            print("  - Company")
            print("  - Position")
            print("  - Connected On")
            
            # Read first few rows
            print("\nFirst 3 connections:")
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                name = f"{row.get('First Name', '')} {row.get('Last Name', '')}"
                company = row.get('Company', 'N/A')
                print(f"  {i+1}. {name} - {company}")
        
        return 0
    
    # Import connections
    logger.info(f"Starting import from {args.csv_file}")
    stats = import_connections(args.csv_file, args.exclude)
    
    # Print summary
    print("\n📊 Import Summary:")
    print(f"Total rows: {stats['total_rows']}")
    print(f"Imported: {stats['imported']}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        print("\n⚠️  Some errors occurred. Check logs for details.")
        return 1
    else:
        print("\n✅ Import completed successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())