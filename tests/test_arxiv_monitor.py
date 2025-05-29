"""
Pytest tests for ArxivMonitor class.
"""

import os
import pytest
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock, Mock
import arxiv

from src.collectors.arxiv_monitor import ArxivMonitor
from src.models.paper import Paper
from src.models.base import Base, engine


class TestArxivMonitor:
    """Test cases for ArxivMonitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create ArxivMonitor instance for testing."""
        with patch.dict(os.environ, {
            "ARXIV_CATEGORIES": "cs.AI,cs.CL",
            "ARXIV_MAX_RESULTS_PER_DAY": "10",
            "ARXIV_LOOKBACK_DAYS": "3",
            "TOPICS": "ai safety,alignment,interpretability",
            "MIN_RELEVANCE_SCORE": "0.6"
        }):
            return ArxivMonitor()
    
    @pytest.fixture
    def mock_arxiv_result(self):
        """Create a mock arxiv.Result object."""
        result = Mock(spec=arxiv.Result)
        result.entry_id = "http://arxiv.org/abs/2312.00752v1"
        result.title = "Mechanistic Interpretability in AI Safety Research"
        result.summary = "This paper explores mechanistic interpretability methods for ensuring AI alignment and safety."
        result.authors = [Mock(name="John Doe"), Mock(name="Jane Smith")]
        result.published = datetime(2023, 12, 15, 10, 30, 0)
        result.pdf_url = "http://arxiv.org/pdf/2312.00752v1"
        result.categories = ["cs.AI", "cs.LG"]
        return result
    
    @pytest.fixture
    def setup_test_db(self):
        """Setup test database."""
        # Create all tables
        Base.metadata.create_all(bind=engine)
        yield
        # Cleanup - drop all tables
        Base.metadata.drop_all(bind=engine)
    
    def test_initialization(self, monitor):
        """Test monitor initialization with environment variables."""
        assert monitor.categories == ["cs.AI", "cs.CL"]
        assert monitor.max_results == 10
        assert monitor.lookback_days == 3
        assert "ai safety" in monitor.topics
        assert "alignment" in monitor.topics
    
    def test_extract_arxiv_id(self, monitor):
        """Test arXiv ID extraction from various formats."""
        test_cases = [
            ("http://arxiv.org/abs/2312.00752v1", "2312.00752"),
            ("http://arxiv.org/abs/1706.03762", "1706.03762"),
            ("https://arxiv.org/abs/2301.12345v2", "2301.12345"),
            ("2312.00752", "2312.00752"),  # Already extracted
        ]
        
        for entry_id, expected in test_cases:
            assert monitor.extract_arxiv_id(entry_id) == expected
    
    def test_calculate_relevance_score(self, monitor, mock_arxiv_result):
        """Test relevance score calculation."""
        score, keywords = monitor.calculate_relevance_score(mock_arxiv_result)
        
        # Should have high score due to title and abstract matches
        assert score > 0.3
        assert len(keywords) > 0
        assert any("interpretability" in kw for kw in keywords)
        assert any("safety" in kw for kw in keywords)
    
    def test_calculate_relevance_score_low(self, monitor):
        """Test relevance score for unrelated paper."""
        result = Mock(spec=arxiv.Result)
        result.title = "Deep Learning for Image Classification"
        result.summary = "This paper presents a new CNN architecture for ImageNet."
        result.authors = [Mock(name="Random Author")]
        
        score, keywords = monitor.calculate_relevance_score(result)
        
        assert score < 0.3
        assert len(keywords) == 0
    
    def test_calculate_relevance_score_known_researcher(self, monitor):
        """Test relevance score boost for known researchers."""
        result = Mock(spec=arxiv.Result)
        result.title = "Some Random Paper"
        result.summary = "Random abstract text"
        result.authors = [Mock(name="Stuart Russell"), Mock(name="Other Author")]
        
        score, keywords = monitor.calculate_relevance_score(result)
        
        assert score >= 0.2  # Boost from known researcher
        assert any("stuart russell" in kw for kw in keywords)
    
    def test_extract_arxiv_mentions(self, monitor):
        """Test extraction of arXiv IDs from text."""
        text = """
        Check out this great paper arxiv:2312.00752 on interpretability.
        Also see arXiv:1706.03762 for the transformer architecture.
        The paper at https://arxiv.org/abs/2301.12345 is also relevant.
        Random numbers like 1234.5678 shouldn't match.
        """
        
        ids = monitor.extract_arxiv_mentions(text)
        
        assert "2312.00752" in ids
        assert "1706.03762" in ids
        assert "2301.12345" in ids
        assert "1234.5678" not in ids  # Invalid format
    
    @patch('arxiv.Search')
    def test_search_papers(self, mock_search_class, monitor):
        """Test paper search functionality."""
        # Mock search results
        mock_results = [
            Mock(published=datetime.utcnow() - timedelta(days=1)),
            Mock(published=datetime.utcnow() - timedelta(days=2)),
            Mock(published=datetime.utcnow() - timedelta(days=10)),  # Too old
        ]
        
        mock_search = Mock()
        mock_search.results.return_value = mock_results
        mock_search_class.return_value = mock_search
        
        # Search papers
        start_date = (datetime.utcnow() - timedelta(days=3)).date()
        results = monitor.search_papers(start_date)
        
        # Should only return recent papers
        assert len(results) == 2
        
        # Verify search parameters
        mock_search_class.assert_called_once()
        call_args = mock_search_class.call_args[1]
        assert "cs.AI" in call_args['query']
        assert "cs.CL" in call_args['query']
        assert call_args['max_results'] == 10
    
    @patch.object(ArxivMonitor, 'llm_config')
    def test_summarize_paper(self, mock_llm, monitor, mock_arxiv_result):
        """Test paper summarization with LLM."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="This paper introduces new methods for interpretability."))]
        mock_llm.complete.return_value = mock_response
        
        summary = monitor.summarize_paper(mock_arxiv_result)
        
        assert summary is not None
        assert "interpretability" in summary
        
        # Verify LLM was called correctly
        mock_llm.complete.assert_called_once()
        messages = mock_llm.complete.call_args[0][0]
        assert len(messages) == 2
        assert "AI safety researcher" in messages[0]["content"]
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_store_paper(self, monitor, mock_arxiv_result):
        """Test storing a paper in the database."""
        from src.models.base import SessionLocal
        
        db = SessionLocal()
        try:
            # Store paper
            paper = monitor.store_paper(mock_arxiv_result, db)
            
            assert paper is not None
            assert paper.arxiv_id == "2312.00752"
            assert paper.title == mock_arxiv_result.title
            assert len(paper.authors) == 2
            assert paper.relevance_score > 0
            
            # Try storing again - should return None (duplicate)
            duplicate = monitor.store_paper(mock_arxiv_result, db)
            assert duplicate is None
            
        finally:
            db.close()
    
    @pytest.mark.usefixtures("setup_test_db")
    @patch.object(ArxivMonitor, 'search_papers')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_collect_papers(self, mock_sleep, mock_search, monitor, mock_arxiv_result):
        """Test the main paper collection method."""
        # Mock search results
        mock_search.return_value = [mock_arxiv_result]
        
        # Run collection
        stats = monitor.collect_papers()
        
        assert stats["searched"] == 1
        assert stats["stored"] == 1
        assert stats["skipped"] == 0
        assert stats["relevant"] == 1
        assert stats["errors"] == 0
        
        # Verify paper was stored
        from src.models.base import SessionLocal
        db = SessionLocal()
        try:
            paper = db.query(Paper).filter_by(arxiv_id="2312.00752").first()
            assert paper is not None
            assert paper.processed is False  # Not yet processed
        finally:
            db.close()
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_find_papers_by_ids(self, monitor):
        """Test finding papers by their IDs."""
        from src.models.base import SessionLocal
        
        # First, add some test papers
        db = SessionLocal()
        try:
            papers_data = [
                {"arxiv_id": "2312.00001", "title": "Paper 1", "authors": [], "abstract": "Test", 
                 "pdf_url": "http://test.com", "categories": ["cs.AI"], "submission_date": date.today()},
                {"arxiv_id": "2312.00002", "title": "Paper 2", "authors": [], "abstract": "Test", 
                 "pdf_url": "http://test.com", "categories": ["cs.AI"], "submission_date": date.today()},
                {"arxiv_id": "2312.00003", "title": "Paper 3", "authors": [], "abstract": "Test", 
                 "pdf_url": "http://test.com", "categories": ["cs.AI"], "submission_date": date.today()},
            ]
            
            for data in papers_data:
                paper = Paper(**data)
                db.add(paper)
            db.commit()
        finally:
            db.close()
        
        # Test finding papers
        found = monitor.find_papers_by_ids(["2312.00001", "2312.00003", "2312.99999"])
        
        assert len(found) == 2
        assert any(p.arxiv_id == "2312.00001" for p in found)
        assert any(p.arxiv_id == "2312.00003" for p in found)
        assert not any(p.arxiv_id == "2312.00002" for p in found)


class TestIntegration:
    """Integration tests that may require external services."""
    
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true",
        reason="Skipping integration tests"
    )
    def test_real_arxiv_search(self):
        """Test actual arXiv API search (requires internet)."""
        monitor = ArxivMonitor()
        monitor.max_results = 5  # Limit for testing
        
        # Search for papers from last 30 days
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        papers = monitor.search_papers(start_date)
        
        assert len(papers) > 0
        assert all(hasattr(p, 'title') for p in papers)
        assert all(hasattr(p, 'entry_id') for p in papers)