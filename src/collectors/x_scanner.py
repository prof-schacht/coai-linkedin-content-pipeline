"""
X.com (Twitter) scanner for AI safety discussions.
Uses web scraping to avoid API costs while respecting rate limits.
"""

import os
import re
import time
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.x_post import XPost
from src.collectors.arxiv_monitor import ArxivMonitor

logger = logging.getLogger(__name__)


class XScanner:
    """Scanner for X.com posts about AI safety topics."""
    
    def __init__(self):
        # Load configuration
        self.search_queries = os.getenv(
            "X_SEARCH_QUERIES",
            "AI safety,AI alignment,mechanistic interpretability,AI control,technical AI governance"
        ).split(",")
        self.search_queries = [q.strip() for q in self.search_queries]
        
        self.max_posts_per_query = int(os.getenv("X_MAX_POSTS_PER_QUERY", "100"))
        self.scraping_delay = int(os.getenv("X_SCRAPING_DELAY", "3"))
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Known AI safety accounts (for relevance scoring)
        self.known_accounts = [
            "anth_prabhu", "sama", "elonmusk", "demishassabis", "geoffreyhinton",
            "ylecun", "goodfellow_ian", "tegmark", "stuartjrussell", "nickbostrom",
            "paulfchristiano", "catherineols", "jackclarkSF", "Miles_Brundage"
        ]
        
        self.arxiv_monitor = ArxivMonitor()
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent for requests."""
        return random.choice(self.user_agents)
    
    def build_search_url(self, query: str, cursor: Optional[str] = None) -> str:
        """
        Build X.com search URL for a query.
        Note: X.com's search may require authentication for full results.
        """
        encoded_query = quote(f"{query} min_faves:10")  # Filter for quality
        base_url = f"https://x.com/search?q={encoded_query}&f=live"
        
        if cursor:
            base_url += f"&cursor={cursor}"
            
        return base_url
    
    async def setup_browser(self) -> Tuple[Browser, Page]:
        """Set up Playwright browser with stealth settings."""
        playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        # Create context with random user agent
        context = await browser.new_context(
            user_agent=self.get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        
        # Create page
        page = await context.new_page()
        
        # Add stealth scripts
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return browser, page
    
    async def wait_random_delay(self, min_seconds: int = 2, max_seconds: int = 5):
        """Wait for a random delay to appear more human-like."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract post ID from X.com URL."""
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else None
    
    def extract_numbers(self, text: str) -> int:
        """Extract number from engagement text (e.g., '1.2K' -> 1200)."""
        if not text:
            return 0
            
        text = text.strip().upper()
        multipliers = {'K': 1000, 'M': 1000000}
        
        for suffix, multiplier in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, '').replace(',', ''))
                    return int(num * multiplier)
                except:
                    return 0
        
        try:
            return int(text.replace(',', ''))
        except:
            return 0
    
    async def extract_post_data(self, post_element, page: Page) -> Optional[Dict]:
        """Extract data from a single post element."""
        try:
            # Get post HTML
            post_html = await post_element.inner_html()
            soup = BeautifulSoup(post_html, 'html.parser')
            
            # Extract post URL and ID
            post_link = soup.find('a', {'href': re.compile(r'/status/\d+')})
            if not post_link:
                return None
                
            post_url = post_link.get('href', '')
            post_id = self.extract_post_id(post_url)
            if not post_id:
                return None
            
            # Extract author info
            author_link = soup.find('a', {'href': re.compile(r'^/[^/]+$')})
            if not author_link:
                return None
                
            author_handle = author_link.get('href', '').strip('/')
            author_name = author_link.get_text(strip=True)
            
            # Extract content
            content_div = soup.find('div', {'data-testid': 'tweetText'})
            if not content_div:
                # Try alternative selectors
                content_div = soup.find('div', {'lang': True})
            
            content = content_div.get_text(strip=True) if content_div else ""
            
            # Extract timestamp
            time_element = soup.find('time')
            posted_at = None
            if time_element and time_element.get('datetime'):
                posted_at = datetime.fromisoformat(time_element['datetime'].replace('Z', '+00:00'))
            
            # Extract engagement metrics
            metrics = {
                'likes': 0,
                'retweets': 0,
                'replies': 0
            }
            
            # Look for engagement buttons/text
            for metric_type in ['like', 'retweet', 'reply']:
                metric_element = soup.find('div', {'data-testid': f'{metric_type}'})
                if metric_element:
                    metric_text = metric_element.get_text(strip=True)
                    metrics[f'{metric_type}s'] = self.extract_numbers(metric_text)
            
            # Extract URLs
            mentioned_urls = []
            for link in soup.find_all('a', {'href': re.compile(r'^https?://')}):
                url = link.get('href', '')
                if 'x.com' not in url and 'twitter.com' not in url:
                    mentioned_urls.append(url)
            
            # Extract mentions
            mentioned_users = []
            for mention in soup.find_all('a', {'href': re.compile(r'^/@')}):
                username = mention.get('href', '').strip('/@')
                if username:
                    mentioned_users.append(username)
            
            # Extract hashtags
            hashtags = []
            for tag in soup.find_all('a', {'href': re.compile(r'/hashtag/')}):
                hashtag = tag.get_text(strip=True).strip('#')
                if hashtag:
                    hashtags.append(hashtag)
            
            return {
                'post_id': post_id,
                'author_handle': author_handle,
                'author_name': author_name,
                'content': content,
                'posted_at': posted_at,
                'likes': metrics['likes'],
                'retweets': metrics['retweets'],
                'replies': metrics['replies'],
                'mentioned_urls': mentioned_urls,
                'mentioned_users': mentioned_users,
                'hashtags': hashtags
            }
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None
    
    async def search_posts(self, query: str, max_posts: int = 50) -> List[Dict]:
        """Search for posts matching a query."""
        posts = []
        browser = None
        
        try:
            # Setup browser
            browser, page = await self.setup_browser()
            
            # Navigate to search
            search_url = self.build_search_url(query)
            logger.info(f"Searching X.com for: {query}")
            logger.debug(f"URL: {search_url}")
            
            await page.goto(search_url, wait_until='networkidle')
            await self.wait_random_delay(3, 5)
            
            # Scroll to load posts
            posts_collected = 0
            last_height = 0
            no_change_count = 0
            
            while posts_collected < max_posts and no_change_count < 3:
                # Get current posts
                post_elements = await page.query_selector_all('article[data-testid="tweet"]')
                
                for element in post_elements[posts_collected:]:
                    if posts_collected >= max_posts:
                        break
                        
                    post_data = await self.extract_post_data(element, page)
                    if post_data and post_data['post_id'] not in [p['post_id'] for p in posts]:
                        posts.append(post_data)
                        posts_collected += 1
                        logger.debug(f"Collected post {posts_collected}: {post_data['post_id']}")
                
                # Scroll down
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await self.wait_random_delay(2, 4)
                
                # Check if page height changed
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    no_change_count += 1
                else:
                    no_change_count = 0
                last_height = new_height
            
            logger.info(f"Collected {len(posts)} posts for query: {query}")
            
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
        
        finally:
            if browser:
                await browser.close()
        
        return posts
    
    def calculate_relevance_score(self, post: Dict) -> float:
        """Calculate relevance score for a post."""
        score = 0.0
        content_lower = post['content'].lower()
        
        # Check for AI safety keywords
        ai_safety_keywords = [
            "ai safety", "ai alignment", "ai risk", "existential risk",
            "interpretability", "mechanistic", "control problem",
            "mesa-optimization", "inner alignment", "outer alignment"
        ]
        
        for keyword in ai_safety_keywords:
            if keyword in content_lower:
                score += 0.2
        
        # Check for known accounts
        if post['author_handle'].lower() in [acc.lower() for acc in self.known_accounts]:
            score += 0.3
        
        # Engagement bonus
        engagement = post['likes'] + post['retweets'] * 2 + post['replies'] * 3
        if engagement > 1000:
            score += 0.2
        elif engagement > 100:
            score += 0.1
        
        # URL bonus (likely sharing papers/articles)
        if post['mentioned_urls']:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def extract_arxiv_refs(self, post: Dict) -> List[str]:
        """Extract arXiv paper references from post."""
        arxiv_refs = []
        
        # Check content for arXiv IDs
        content_refs = self.arxiv_monitor.extract_arxiv_mentions(post['content'])
        arxiv_refs.extend(content_refs)
        
        # Check URLs for arXiv links
        for url in post.get('mentioned_urls', []):
            if 'arxiv.org' in url:
                # Extract ID from URL
                match = re.search(r'(\d{4}\.\d{4,5})', url)
                if match:
                    arxiv_refs.append(match.group(1))
        
        return list(set(arxiv_refs))  # Remove duplicates
    
    def store_post(self, post_data: Dict, db: Session) -> Optional[XPost]:
        """Store a post in the database."""
        # Check if already exists
        existing = db.query(XPost).filter_by(post_id=post_data['post_id']).first()
        if existing:
            logger.debug(f"Post {post_data['post_id']} already exists")
            return None
        
        # Calculate relevance score
        relevance_score = self.calculate_relevance_score(post_data)
        
        # Extract arXiv references
        arxiv_refs = self.extract_arxiv_refs(post_data)
        
        # Determine if viral
        engagement = post_data['likes'] + post_data['retweets'] * 2 + post_data['replies'] * 3
        is_viral = engagement > 1000
        
        # Create post record
        db_post = XPost(
            post_id=post_data['post_id'],
            author_handle=post_data['author_handle'],
            author_name=post_data['author_name'],
            content=post_data['content'],
            posted_at=post_data['posted_at'] or datetime.utcnow(),
            likes=post_data['likes'],
            retweets=post_data['retweets'],
            replies=post_data['replies'],
            mentioned_urls=post_data.get('mentioned_urls', []),
            mentioned_users=post_data.get('mentioned_users', []),
            hashtags=post_data.get('hashtags', []),
            arxiv_refs=arxiv_refs,
            relevance_score=relevance_score,
            is_viral=is_viral
        )
        
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        
        logger.info(f"Stored post: {post_data['post_id']} by @{post_data['author_handle']} (relevance: {relevance_score:.2f})")
        return db_post
    
    async def scan_all_queries(self) -> Dict[str, int]:
        """Scan all configured search queries."""
        stats = {
            "queries": len(self.search_queries),
            "posts_found": 0,
            "posts_stored": 0,
            "posts_skipped": 0,
            "arxiv_refs_found": 0,
            "errors": 0
        }
        
        with get_db() as db:
            for query in self.search_queries:
                try:
                    logger.info(f"Scanning query: {query}")
                    
                    # Search posts
                    posts = await self.search_posts(query, self.max_posts_per_query)
                    stats["posts_found"] += len(posts)
                    
                    # Store posts
                    for post_data in posts:
                        try:
                            stored_post = self.store_post(post_data, db)
                            if stored_post:
                                stats["posts_stored"] += 1
                                stats["arxiv_refs_found"] += len(stored_post.arxiv_refs or [])
                            else:
                                stats["posts_skipped"] += 1
                        except Exception as e:
                            logger.error(f"Error storing post: {e}")
                            stats["errors"] += 1
                    
                    # Rate limiting between queries
                    await self.wait_random_delay(self.scraping_delay, self.scraping_delay + 2)
                    
                except Exception as e:
                    logger.error(f"Error scanning query '{query}': {e}")
                    stats["errors"] += 1
        
        logger.info(f"Scan complete: {stats}")
        return stats
    
    def get_trending_topics(self, hours: int = 24) -> List[Dict]:
        """Get trending topics from recent posts."""
        with get_db() as db:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get high-engagement posts
            viral_posts = db.query(XPost).filter(
                XPost.posted_at >= since,
                XPost.is_viral == True
            ).order_by(XPost.likes.desc()).limit(20).all()
            
            # Extract topics from hashtags and content
            topics = {}
            for post in viral_posts:
                # Count hashtags
                for tag in (post.hashtags or []):
                    tag_lower = tag.lower()
                    if tag_lower not in topics:
                        topics[tag_lower] = {'count': 0, 'engagement': 0}
                    topics[tag_lower]['count'] += 1
                    topics[tag_lower]['engagement'] += post.engagement_score
            
            # Sort by engagement
            trending = []
            for topic, data in topics.items():
                trending.append({
                    'topic': topic,
                    'count': data['count'],
                    'engagement': data['engagement']
                })
            
            trending.sort(key=lambda x: x['engagement'], reverse=True)
            return trending[:10]