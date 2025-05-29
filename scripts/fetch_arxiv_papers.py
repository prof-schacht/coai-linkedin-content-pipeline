#!/usr/bin/env python3
"""
Daily script to fetch and process arXiv papers.
Can be run manually or via cron job.
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta, date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.arxiv_monitor import ArxivMonitor
from src.models.base import init_db, get_db
from src.models.paper import Paper
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/arxiv_fetch.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def setup_logging_dir():
    """Ensure logs directory exists."""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
        logger.info("Created logs directory")


def get_recent_papers_stats(db):
    """Get statistics about recently collected papers."""
    # Papers from last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    total_papers = db.query(Paper).count()
    recent_papers = db.query(Paper).filter(Paper.created_at >= week_ago).count()
    relevant_papers = db.query(Paper).filter(
        Paper.relevance_score >= float(os.getenv("MIN_RELEVANCE_SCORE", "0.6"))
    ).count()
    
    return {
        "total": total_papers,
        "recent": recent_papers,
        "relevant": relevant_papers
    }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Fetch arXiv papers for AI safety topics")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days to look back (overrides ARXIV_LOOKBACK_DAYS)"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date to start from (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without storing"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show database statistics"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_logging_dir()
    logger.info("=" * 50)
    logger.info("Starting arXiv paper fetch")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1
    
    # Show statistics only
    if args.stats_only:
        with get_db() as db:
            stats = get_recent_papers_stats(db)
            print("\n📊 Database Statistics:")
            print(f"Total papers: {stats['total']}")
            print(f"Recent papers (7 days): {stats['recent']}")
            print(f"Relevant papers: {stats['relevant']}")
        return 0
    
    # Create monitor
    monitor = ArxivMonitor()
    
    # Override lookback days if specified
    if args.days:
        monitor.lookback_days = args.days
        logger.info(f"Overriding lookback days to: {args.days}")
    
    # Parse start date if specified
    start_date = None
    if args.date:
        try:
            start_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            logger.info(f"Starting from specific date: {start_date}")
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            return 1
    
    # Dry run - just search and show results
    if args.dry_run:
        logger.info("DRY RUN - No papers will be stored")
        papers = monitor.search_papers(start_date)
        
        print(f"\n📚 Found {len(papers)} papers:")
        for i, paper in enumerate(papers[:10], 1):  # Show first 10
            score, keywords = monitor.calculate_relevance_score(paper)
            print(f"\n{i}. {paper.title}")
            print(f"   Authors: {', '.join([a.name for a in paper.authors[:3]])}")
            print(f"   Date: {paper.published.date()}")
            print(f"   Relevance: {score:.2f}")
            print(f"   Keywords: {', '.join(keywords[:5])}")
        
        if len(papers) > 10:
            print(f"\n... and {len(papers) - 10} more papers")
        
        return 0
    
    # Actual paper collection
    try:
        logger.info("Starting paper collection...")
        stats = monitor.collect_papers(start_date)
        
        # Log results
        logger.info("Collection completed successfully")
        logger.info(f"Papers searched: {stats['searched']}")
        logger.info(f"Papers stored: {stats['stored']}")
        logger.info(f"Papers skipped (duplicates): {stats['skipped']}")
        logger.info(f"Relevant papers: {stats['relevant']}")
        logger.info(f"Errors: {stats['errors']}")
        
        # Show summary
        print("\n✅ Paper Collection Complete!")
        print(f"📊 Summary:")
        print(f"  - Searched: {stats['searched']} papers")
        print(f"  - Stored: {stats['stored']} new papers")
        print(f"  - Relevant: {stats['relevant']} papers (score >= {os.getenv('MIN_RELEVANCE_SCORE', '0.6')})")
        
        if stats['errors'] > 0:
            print(f"  - ⚠️  Errors: {stats['errors']}")
        
        # Show database stats
        with get_db() as db:
            db_stats = get_recent_papers_stats(db)
            print(f"\n📈 Database now contains:")
            print(f"  - Total: {db_stats['total']} papers")
            print(f"  - Relevant: {db_stats['relevant']} papers")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error during collection: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("Script finished")
        logger.info("=" * 50)


if __name__ == "__main__":
    sys.exit(main())