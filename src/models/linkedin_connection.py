"""
LinkedIn connection model for network analysis.
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Date, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class LinkedInConnection(Base):
    """Model for storing LinkedIn connections with privacy protection."""
    
    __tablename__ = "linkedin_connections"
    
    id = Column(Integer, primary_key=True)
    
    # Privacy-protected identifier (SHA256 hash of email)
    connection_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Public information
    full_name = Column(Text, nullable=False)
    company = Column(Text)
    position = Column(Text)
    location = Column(Text)
    connected_date = Column(Date)
    
    # Analysis results
    expertise_tags = Column(ARRAY(String))
    ai_safety_score = Column(Float, default=0.0, index=True)
    interview_potential_score = Column(Float, default=0.0, index=True)
    mention_relevance_score = Column(Float, default=0.0)
    
    # Network metrics
    connection_degree = Column(Integer, default=1)  # 1st, 2nd, 3rd degree
    mutual_connections = Column(Integer, default=0)
    is_verified_expert = Column(Boolean, default=False)
    
    # Cross-references
    matched_author_names = Column(JSONB)  # Papers they've authored
    matched_social_handles = Column(JSONB)  # X.com handles if found
    
    # Activity tracking
    posts_about_ai = Column(Integer, default=0)
    last_mentioned_date = Column(Date)
    mention_count = Column(Integer, default=0)
    
    # Metadata
    last_analyzed = Column(DateTime)
    excluded_from_analysis = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_linkedin_expertise_scores', 'ai_safety_score', 'interview_potential_score'),
        Index('idx_linkedin_expertise_tags', 'expertise_tags', postgresql_using='gin'),
        Index('idx_linkedin_company_position', 'company', 'position'),
    )
    
    def __repr__(self):
        return f"<LinkedInConnection(name='{self.full_name}', company='{self.company}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'company': self.company,
            'position': self.position,
            'expertise_tags': self.expertise_tags,
            'ai_safety_score': self.ai_safety_score,
            'interview_potential_score': self.interview_potential_score,
            'connection_degree': self.connection_degree,
            'matched_author_names': self.matched_author_names,
            'last_analyzed': self.last_analyzed.isoformat() if self.last_analyzed else None
        }
    
    @property
    def is_ai_expert(self):
        """Check if connection is an AI expert."""
        return self.ai_safety_score >= 7.0
    
    @property
    def is_good_interview_candidate(self):
        """Check if connection is a good interview candidate."""
        return self.interview_potential_score >= 7.5


class ExpertiseMapping(Base):
    """Model for mapping keywords to expertise areas."""
    
    __tablename__ = "expertise_mappings"
    
    id = Column(Integer, primary_key=True)
    expertise_area = Column(String(50), nullable=False, index=True)
    keywords = Column(JSONB, nullable=False)  # List of keywords
    weight = Column(Float, default=1.0)  # Importance weight
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExpertiseMapping(area='{self.expertise_area}', keywords={len(self.keywords or [])})>"