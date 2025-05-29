"""
Paper model for storing arXiv papers.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, 
    DateTime, Date, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class Paper(Base):
    """Model for storing arXiv papers."""
    
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True)
    arxiv_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    authors = Column(JSONB, nullable=False)  # List of author names and affiliations
    abstract = Column(Text, nullable=False)
    pdf_url = Column(Text, nullable=False)
    categories = Column(JSONB, nullable=False)  # List of categories like ['cs.AI', 'cs.CL']
    submission_date = Column(Date, nullable=False, index=True)
    
    # AI safety relevance scoring
    relevance_score = Column(Float, default=0.0, index=True)
    keyword_matches = Column(JSONB)  # Which keywords were found
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)
    summarized = Column(Boolean, default=False)
    summary = Column(Text)  # LLM-generated summary
    
    # Extracted content
    figures_extracted = Column(Boolean, default=False)
    figure_urls = Column(JSONB)  # List of extracted figure URLs
    
    # Cross-references
    mentioned_in_posts = Column(JSONB)  # X.com post IDs that mention this paper
    citation_count = Column(Integer, default=0)  # Estimated citations
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_papers_submission_relevance', 'submission_date', 'relevance_score'),
        Index('idx_papers_processed_date', 'processed', 'submission_date'),
        Index('idx_papers_categories', 'categories', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Paper(arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"
    
    def to_dict(self):
        """Convert paper to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'pdf_url': self.pdf_url,
            'categories': self.categories,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'relevance_score': self.relevance_score,
            'keyword_matches': self.keyword_matches,
            'processed': self.processed,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }