"""
Pytest tests for XScanner class.
"""

import os
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from bs4 import BeautifulSoup

from src.collectors.x_scanner import XScanner
from src.models.x_post import XPost
from src.models.base import Base, engine


class TestXScanner:
    """Test cases for XScanner."""
    
    @pytest.fixture
    def scanner(self):
        """Create XScanner instance for testing."""
        with patch.dict(os.environ, {
            "X_SEARCH_QUERIES": "AI safety,AI alignment",
            "X_MAX_POSTS_PER_QUERY": "10",
            "X_SCRAPING_DELAY": "1",
            "MIN_RELEVANCE_SCORE": "0.6"
        }):
            return XScanner()
    
    @pytest.fixture
    def mock_post_element(self):
        """Create a mock post element with HTML."""
        html = """
        <article data-testid="tweet">
            <a href="/elonmusk">Elon Musk</a>
            <a href="/elonmusk/status/1234567890">
                <time datetime="2024-01-15T10:30:00.000Z">Jan 15</time>
            </a>
            <div data-testid="tweetText">
                Discussing AI safety and alignment is crucial. 
                Check out this paper: https://arxiv.org/abs/2312.00752
                #AISafety #AIAlignment
            </div>
            <div data-testid="like">1.2K</div>
            <div data-testid="retweet">500</div>
            <div data-testid="reply">250</div>
            <a href="/@anthropic">@anthropic</a>
            <a href="/hashtag/AISafety">#AISafety</a>
        </article>
        """
        element = AsyncMock()
        element.inner_html = AsyncMock(return_value=html)
        return element
    
    @pytest.fixture
    def setup_test_db(self):
        """Setup test database."""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    def test_initialization(self, scanner):
        """Test scanner initialization."""
        assert scanner.search_queries == ["AI safety", "AI alignment"]
        assert scanner.max_posts_per_query == 10
        assert scanner.scraping_delay == 1
        assert len(scanner.user_agents) > 0
        assert len(scanner.known_accounts) > 0
    
    def test_get_random_user_agent(self, scanner):
        """Test user agent rotation."""
        agents = set()
        for _ in range(10):
            agent = scanner.get_random_user_agent()
            agents.add(agent)
            assert "Mozilla" in agent
        
        # Should have multiple different agents
        assert len(agents) > 1
    
    def test_build_search_url(self, scanner):
        """Test search URL construction."""
        url = scanner.build_search_url("AI safety")
        assert "x.com/search" in url
        assert "AI%20safety" in url
        assert "min_faves%3A10" in url  # Quality filter
        
        # Test with cursor
        url_with_cursor = scanner.build_search_url("AI safety", cursor="abc123")
        assert "cursor=abc123" in url_with_cursor
    
    def test_extract_post_id(self, scanner):
        """Test post ID extraction."""
        test_cases = [
            ("/user/status/1234567890", "1234567890"),
            ("https://x.com/user/status/9876543210", "9876543210"),
            ("/status/1111111111", "1111111111"),
            ("invalid-url", None)
        ]
        
        for url, expected in test_cases:
            assert scanner.extract_post_id(url) == expected
    
    def test_extract_numbers(self, scanner):
        """Test number extraction from engagement text."""
        test_cases = [
            ("1.2K", 1200),
            ("500", 500),
            ("2.5M", 2500000),
            ("1,234", 1234),
            ("", 0),
            ("invalid", 0)
        ]
        
        for text, expected in test_cases:
            assert scanner.extract_numbers(text) == expected
    
    @pytest.mark.asyncio
    async def test_extract_post_data(self, scanner, mock_post_element):
        """Test post data extraction from HTML."""
        page = AsyncMock()
        
        data = await scanner.extract_post_data(mock_post_element, page)
        
        assert data is not None
        assert data['post_id'] == "1234567890"
        assert data['author_handle'] == "elonmusk"
        assert data['author_name'] == "Elon Musk"
        assert "AI safety" in data['content']
        assert data['likes'] == 1200
        assert data['retweets'] == 500
        assert data['replies'] == 250
        assert "https://arxiv.org/abs/2312.00752" in data['mentioned_urls']
        assert "anthropic" in data['mentioned_users']
        assert "AISafety" in data['hashtags']
    
    def test_calculate_relevance_score(self, scanner):
        """Test relevance score calculation."""
        # High relevance post
        post1 = {
            'content': 'Important discussion on AI safety and alignment research',
            'author_handle': 'paulfchristiano',  # Known researcher
            'likes': 2000,
            'retweets': 500,
            'replies': 100,
            'mentioned_urls': ['https://arxiv.org/abs/2312.00752']
        }
        score1 = scanner.calculate_relevance_score(post1)
        assert score1 >= 0.7  # High score
        
        # Low relevance post
        post2 = {
            'content': 'Just had coffee',
            'author_handle': 'random_user',
            'likes': 5,
            'retweets': 0,
            'replies': 1,
            'mentioned_urls': []
        }
        score2 = scanner.calculate_relevance_score(post2)
        assert score2 < 0.3  # Low score
    
    def test_extract_arxiv_refs(self, scanner):
        """Test arXiv reference extraction."""
        post = {
            'content': 'Check out arxiv:2312.00752 and this paper https://arxiv.org/abs/1706.03762',
            'mentioned_urls': [
                'https://arxiv.org/abs/2301.12345',
                'https://example.com'
            ]
        }
        
        refs = scanner.extract_arxiv_refs(post)
        
        assert "2312.00752" in refs
        assert "1706.03762" in refs
        assert "2301.12345" in refs
        assert len(refs) == 3  # No duplicates
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_store_post(self, scanner):
        """Test storing a post in the database."""
        from src.models.base import SessionLocal
        
        post_data = {
            'post_id': '1234567890',
            'author_handle': 'test_user',
            'author_name': 'Test User',
            'content': 'Discussion about AI alignment and safety',
            'posted_at': datetime.utcnow(),
            'likes': 100,
            'retweets': 50,
            'replies': 25,
            'mentioned_urls': ['https://example.com'],
            'mentioned_users': ['anthropic'],
            'hashtags': ['AISafety']
        }
        
        db = SessionLocal()
        try:
            # Store post
            stored = scanner.store_post(post_data, db)
            
            assert stored is not None
            assert stored.post_id == '1234567890'
            assert stored.relevance_score > 0
            assert len(stored.arxiv_refs) == 0  # No arXiv refs in test data
            
            # Try storing again - should return None (duplicate)
            duplicate = scanner.store_post(post_data, db)
            assert duplicate is None
            
        finally:
            db.close()
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_get_trending_topics(self, scanner):
        """Test trending topic extraction."""
        from src.models.base import SessionLocal
        
        db = SessionLocal()
        try:
            # Add some test posts
            for i in range(5):
                post = XPost(
                    post_id=str(i),
                    author_handle=f"user{i}",
                    content=f"Post about #AISafety and #AIAlignment",
                    posted_at=datetime.utcnow() - timedelta(hours=i),
                    likes=1000 * (5-i),
                    retweets=500 * (5-i),
                    replies=100 * (5-i),
                    hashtags=['AISafety', 'AIAlignment'],
                    is_viral=True
                )
                db.add(post)
            db.commit()
        finally:
            db.close()
        
        # Get trending topics
        trending = scanner.get_trending_topics(hours=24)
        
        assert len(trending) > 0
        assert trending[0]['topic'] in ['aisafety', 'aialignment']
        assert trending[0]['count'] == 5
        assert trending[0]['engagement'] > 0
    
    @pytest.mark.asyncio
    @patch('src.collectors.x_scanner.async_playwright')
    async def test_setup_browser(self, mock_playwright, scanner):
        """Test browser setup."""
        # Mock playwright
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_pw = AsyncMock()
        mock_pw.chromium = mock_chromium
        mock_pw.start = AsyncMock(return_value=mock_pw)
        
        mock_playwright.return_value = mock_pw
        
        # Test browser setup
        browser, page = await scanner.setup_browser()
        
        # Verify setup
        mock_chromium.launch.assert_called_once()
        launch_args = mock_chromium.launch.call_args[1]
        assert launch_args['headless'] is True
        assert '--disable-blink-features=AutomationControlled' in launch_args['args']
        
        # Verify page creation
        mock_context.new_page.assert_called_once()
        mock_page.add_init_script.assert_called_once()


class TestIntegration:
    """Integration tests for X.com scanner."""
    
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true",
        reason="Skipping integration tests"
    )
    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test actual X.com search (requires internet and may be blocked)."""
        scanner = XScanner()
        scanner.max_posts_per_query = 5  # Limit for testing
        
        # Note: This test may fail due to X.com blocking or requiring auth
        try:
            posts = await scanner.search_posts("AI safety", max_posts=5)
            assert isinstance(posts, list)
            
            if posts:  # If we got results
                post = posts[0]
                assert 'post_id' in post
                assert 'content' in post
                assert 'author_handle' in post
        except Exception as e:
            # X.com scraping can fail for various reasons
            pytest.skip(f"X.com scraping failed: {e}")