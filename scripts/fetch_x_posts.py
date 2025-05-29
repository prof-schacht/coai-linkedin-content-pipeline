#!/usr/bin/env python3
"""
Daily script to fetch and process X.com posts about AI safety.
Can be run manually or via cron job.
"""

import os
import sys
import logging
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.x_scanner import XScanner
from src.models.base import init_db, get_db
from src.models.x_post import XPost
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/x_fetch.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def setup_logging_dir():
    """Ensure logs directory exists."""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
        logger.info("Created logs directory")


def get_recent_posts_stats(db):
    """Get statistics about recently collected posts."""
    # Posts from last 24 hours
    day_ago = datetime.utcnow() - timedelta(days=1)
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    total_posts = db.query(XPost).count()
    recent_posts = db.query(XPost).filter(XPost.scraped_at >= day_ago).count()
    weekly_posts = db.query(XPost).filter(XPost.scraped_at >= week_ago).count()
    viral_posts = db.query(XPost).filter(XPost.is_viral == True).count()
    relevant_posts = db.query(XPost).filter(
        XPost.relevance_score >= float(os.getenv("MIN_RELEVANCE_SCORE", "0.6"))
    ).count()
    
    # Count posts with arXiv references
    arxiv_posts = db.query(XPost).filter(
        XPost.arxiv_refs != None,
        XPost.arxiv_refs != []
    ).count()
    
    return {
        "total": total_posts,
        "recent_24h": recent_posts,
        "recent_7d": weekly_posts,
        "viral": viral_posts,
        "relevant": relevant_posts,
        "with_arxiv": arxiv_posts
    }


async def main_async():
    """Main async execution function."""
    parser = argparse.ArgumentParser(description="Fetch X.com posts about AI safety topics")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum posts per query (overrides X_MAX_POSTS_PER_QUERY)"
    )
    parser.add_argument(
        "--queries",
        type=str,
        nargs='+',
        help="Specific queries to search (overrides default list)"
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
    parser.add_argument(
        "--trending",
        action="store_true",
        help="Show trending topics from recent posts"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_logging_dir()
    logger.info("=" * 50)
    logger.info("Starting X.com post fetch")
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
            stats = get_recent_posts_stats(db)
            print("\n📊 Database Statistics:")
            print(f"Total posts: {stats['total']}")
            print(f"Posts (24h): {stats['recent_24h']}")
            print(f"Posts (7d): {stats['recent_7d']}")
            print(f"Viral posts: {stats['viral']}")
            print(f"Relevant posts: {stats['relevant']}")
            print(f"Posts with arXiv refs: {stats['with_arxiv']}")
        return 0
    
    # Create scanner
    scanner = XScanner()
    
    # Override settings if specified
    if args.max_posts:
        scanner.max_posts_per_query = args.max_posts
        logger.info(f"Overriding max posts per query to: {args.max_posts}")
    
    if args.queries:
        scanner.search_queries = args.queries
        logger.info(f"Using custom queries: {args.queries}")
    
    # Show trending topics
    if args.trending:
        logger.info("Fetching trending topics...")
        trending = scanner.get_trending_topics(hours=24)
        
        print("\n🔥 Trending Topics (24h):")
        for i, topic in enumerate(trending[:10], 1):
            print(f"{i}. #{topic['topic']} - {topic['count']} posts, {topic['engagement']} engagement")
        
        return 0
    
    # Dry run - just show what would be searched
    if args.dry_run:
        logger.info("DRY RUN - No posts will be stored")
        print(f"\n🔍 Would search for {len(scanner.search_queries)} queries:")
        for i, query in enumerate(scanner.search_queries, 1):
            print(f"{i}. {query}")
        print(f"\nMax posts per query: {scanner.max_posts_per_query}")
        print(f"Total potential posts: {len(scanner.search_queries) * scanner.max_posts_per_query}")
        return 0
    
    # Actual post collection
    try:
        logger.info("Starting post collection...")
        stats = await scanner.scan_all_queries()
        
        # Log results
        logger.info("Collection completed successfully")
        logger.info(f"Queries processed: {stats['queries']}")
        logger.info(f"Posts found: {stats['posts_found']}")
        logger.info(f"Posts stored: {stats['posts_stored']}")
        logger.info(f"Posts skipped (duplicates): {stats['posts_skipped']}")
        logger.info(f"ArXiv references found: {stats['arxiv_refs_found']}")
        logger.info(f"Errors: {stats['errors']}")
        
        # Show summary
        print("\n✅ X.com Collection Complete!")
        print(f"📊 Summary:")
        print(f"  - Queries: {stats['queries']}")
        print(f"  - Found: {stats['posts_found']} posts")
        print(f"  - Stored: {stats['posts_stored']} new posts")
        print(f"  - ArXiv refs: {stats['arxiv_refs_found']} papers mentioned")
        
        if stats['errors'] > 0:
            print(f"  - ⚠️  Errors: {stats['errors']}")
        
        # Show database stats
        with get_db() as db:
            db_stats = get_recent_posts_stats(db)
            print(f"\n📈 Database now contains:")
            print(f"  - Total: {db_stats['total']} posts")
            print(f"  - Relevant: {db_stats['relevant']} posts")
            print(f"  - With arXiv: {db_stats['with_arxiv']} posts")
        
        # Show trending if we collected posts
        if stats['posts_stored'] > 0:
            trending = scanner.get_trending_topics(hours=24)
            if trending:
                print(f"\n🔥 Top trending topics:")
                for topic in trending[:5]:
                    print(f"  - #{topic['topic']} ({topic['engagement']} engagement)")
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error during collection: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("Script finished")
        logger.info("=" * 50)


def main():
    """Wrapper to run async main function."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())