"""
Tests for LinkedIn network analysis functionality.
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch

from src.analyzers.network_mapper import NetworkMapper
from src.analyzers.expert_scorer import ExpertScorer
from src.models.linkedin_connection import LinkedInConnection, ExpertiseMapping
from src.models.base import Base, engine


class TestNetworkMapper:
    """Test cases for NetworkMapper."""
    
    @pytest.fixture
    def mapper(self):
        """Create NetworkMapper instance."""
        return NetworkMapper()
    
    @pytest.fixture
    def sample_connection(self):
        """Create a sample LinkedIn connection."""
        return LinkedInConnection(
            connection_hash="test_hash_123",
            full_name="Dr. Jane Smith",
            company="Anthropic",
            position="AI Safety Researcher",
            connected_date=date.today()
        )
    
    @pytest.fixture
    def setup_test_db(self):
        """Setup test database."""
        # Import all models to ensure they're registered
        from src.models.paper import Paper
        from src.models.x_post import XPost
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    def test_initialization(self, mapper):
        """Test mapper initialization."""
        assert 'ai_safety' in mapper.expertise_keywords
        assert 'alignment' in mapper.expertise_keywords
        assert 'interpretability' in mapper.expertise_keywords
        assert 'anthropic' in mapper.institution_weights
        assert mapper.institution_weights['anthropic'] > 1.5
    
    def test_analyze_expertise_ai_safety(self, mapper):
        """Test expertise analysis for AI safety researcher."""
        connection = LinkedInConnection(
            full_name="Test User",
            company="Anthropic",
            position="AI Safety Researcher"
        )
        
        tags, score = mapper._analyze_expertise(connection)
        
        assert 'ai_safety' in tags
        assert score > 5.0  # Should get good score
    
    def test_analyze_expertise_academic(self, mapper):
        """Test expertise analysis for academic."""
        connection = LinkedInConnection(
            full_name="Prof. Test",
            company="Stanford University",
            position="Professor of Machine Learning"
        )
        
        tags, score = mapper._analyze_expertise(connection)
        
        assert 'ml_research' in tags
        assert score > 3.0
    
    def test_analyze_expertise_technical(self, mapper):
        """Test expertise analysis for engineer."""
        connection = LinkedInConnection(
            full_name="Tech User",
            company="Google",
            position="Software Engineer"
        )
        
        tags, score = mapper._analyze_expertise(connection)
        
        assert 'technical' in tags
        assert score > 2.0
    
    def test_calculate_interview_potential(self, mapper):
        """Test interview potential calculation."""
        connection = LinkedInConnection(
            full_name="Dr. Expert",
            company="DeepMind",
            position="Principal Researcher"
        )
        
        expertise_tags = ['ai_safety', 'interpretability']
        ai_safety_score = 8.0
        
        score = mapper._calculate_interview_potential(
            connection, expertise_tags, ai_safety_score
        )
        
        assert score > 6.0  # Should be high for good candidate
    
    def test_suggest_mentions_for_post(self, mapper, setup_test_db):
        """Test mention suggestions."""
        from src.models.base import SessionLocal
        
        db = SessionLocal()
        try:
            # Add test connection
            connection = LinkedInConnection(
                connection_hash="test_hash",
                full_name="AI Expert",
                company="Anthropic",
                position="AI Safety Researcher",
                expertise_tags=['ai_safety'],
                ai_safety_score=8.0,
                mention_count=0
            )
            db.add(connection)
            db.commit()
            
            # Test mention suggestions
            suggestions = mapper.suggest_mentions_for_post(
                post_topic="ai_safety",
                post_keywords=["safety", "alignment"],
                max_mentions=2
            )
            
            assert len(suggestions) > 0
            assert suggestions[0]['name'] == "AI Expert"
            assert suggestions[0]['relevance_score'] > 0
            
        finally:
            db.close()


class TestExpertScorer:
    """Test cases for ExpertScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create ExpertScorer instance."""
        return ExpertScorer()
    
    @pytest.fixture
    def setup_test_db(self):
        """Setup test database."""
        # Import all models to ensure they're registered
        from src.models.paper import Paper
        from src.models.x_post import XPost
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    def test_score_position_relevance(self, scorer):
        """Test position relevance scoring."""
        connection = LinkedInConnection(
            position="Senior AI Safety Researcher"
        )
        
        score = scorer._score_position_relevance(connection)
        assert score > 7.0  # Should get high score
    
    def test_score_company_prestige(self, scorer):
        """Test company prestige scoring."""
        # Test top tier
        connection1 = LinkedInConnection(company="Anthropic")
        score1 = scorer._score_company_prestige(connection1)
        assert score1 == 10.0
        
        # Test major lab
        connection2 = LinkedInConnection(company="DeepMind")
        score2 = scorer._score_company_prestige(connection2)
        assert score2 == 9.0
        
        # Test university
        connection3 = LinkedInConnection(company="Stanford University")
        score3 = scorer._score_company_prestige(connection3)
        assert score3 == 8.0
    
    def test_score_speaking_experience(self, scorer):
        """Test speaking experience scoring."""
        connection = LinkedInConnection(
            position="Senior Researcher and Conference Speaker"
        )
        
        score = scorer._score_speaking_experience(connection)
        assert score > 6.0
    
    def test_comprehensive_scoring(self, scorer):
        """Test comprehensive expert scoring."""
        connection = LinkedInConnection(
            full_name="Dr. AI Expert",
            company="Anthropic",
            position="Senior AI Safety Researcher and Speaker",
            mutual_connections=30,
            mention_count=0,
            matched_author_names=[
                {"arxiv_id": "2312.00001", "title": "AI Safety Paper"}
            ]
        )
        
        results = scorer.score_expert(connection)
        
        assert 'ai_safety_score' in results
        assert 'interview_potential_score' in results
        assert 'mention_relevance_score' in results
        assert results['ai_safety_score'] > 7.0  # Should be high
        assert results['interview_potential_score'] > 7.0


class TestLinkedInConnectionModel:
    """Test cases for LinkedInConnection model."""
    
    @pytest.fixture
    def setup_test_db(self):
        """Setup test database."""
        # Import all models to ensure they're registered
        from src.models.paper import Paper
        from src.models.x_post import XPost
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_create_connection(self):
        """Test creating a LinkedIn connection."""
        from src.models.base import SessionLocal
        
        db = SessionLocal()
        try:
            connection = LinkedInConnection(
                connection_hash="test_hash_456",
                full_name="Test User",
                company="Test Company",
                position="Test Position",
                ai_safety_score=7.5,
                interview_potential_score=8.0
            )
            
            db.add(connection)
            db.commit()
            db.refresh(connection)
            
            assert connection.id is not None
            assert connection.is_ai_expert == True
            assert connection.is_good_interview_candidate == True
            
        finally:
            db.close()
    
    @pytest.mark.usefixtures("setup_test_db")
    def test_expertise_mapping(self):
        """Test expertise mapping model."""
        from src.models.base import SessionLocal
        
        db = SessionLocal()
        try:
            mapping = ExpertiseMapping(
                expertise_area="test_area",
                keywords=["keyword1", "keyword2"],
                weight=1.5
            )
            
            db.add(mapping)
            db.commit()
            db.refresh(mapping)
            
            assert mapping.id is not None
            assert mapping.expertise_area == "test_area"
            assert len(mapping.keywords) == 2
            
        finally:
            db.close()