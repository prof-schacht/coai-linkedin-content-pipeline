"""
X.com (Twitter) post model for storing scraped discussions.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class XPost(Base):
    """Model for storing X.com posts about AI safety topics."""
    
    __tablename__ = "x_posts"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Author information
    author_handle = Column(String(100), nullable=False, index=True)
    author_name = Column(Text)
    author_verified = Column(Boolean, default=False)
    author_followers = Column(Integer)
    
    # Post content
    content = Column(Text, nullable=False)
    posted_at = Column(DateTime, nullable=False, index=True)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0) 
    replies = Column(Integer, default=0)
    views = Column(Integer)  # If available
    
    # Thread information
    thread_id = Column(String(50), index=True)  # Root post ID if part of thread
    is_thread_starter = Column(Boolean, default=False)
    reply_to_id = Column(String(50))  # Direct parent if reply
    
    # Extracted data
    mentioned_urls = Column(JSONB)  # List of URLs mentioned
    mentioned_users = Column(JSONB)  # List of @mentions
    hashtags = Column(JSONB)  # List of hashtags
    arxiv_refs = Column(ARRAY(String))  # Extracted arXiv paper IDs
    
    # Analysis
    relevance_score = Column(Float, default=0.0, index=True)
    sentiment_score = Column(Float)  # -1 to 1
    is_viral = Column(Boolean, default=False)  # High engagement threshold
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)
    paper_refs_extracted = Column(Boolean, default=False)
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_xposts_posted_relevance', 'posted_at', 'relevance_score'),
        Index('idx_xposts_author_date', 'author_handle', 'posted_at'),
        Index('idx_xposts_engagement', 'likes', 'retweets'),
        Index('idx_xposts_arxiv_refs', 'arxiv_refs', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<XPost(post_id='{self.post_id}', author='@{self.author_handle}', content='{self.content[:50]}...')>"
    
    def to_dict(self):
        """Convert post to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'post_id': self.post_id,
            'author_handle': self.author_handle,
            'author_name': self.author_name,
            'content': self.content,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'likes': self.likes,
            'retweets': self.retweets,
            'replies': self.replies,
            'thread_id': self.thread_id,
            'mentioned_urls': self.mentioned_urls,
            'arxiv_refs': self.arxiv_refs,
            'relevance_score': self.relevance_score,
            'is_viral': self.is_viral
        }
    
    @property
    def engagement_score(self):
        """Calculate overall engagement score."""
        return (self.likes or 0) + (self.retweets or 0) * 2 + (self.replies or 0) * 3
    
    @property
    def url(self):
        """Construct X.com URL for this post."""
        return f"https://x.com/{self.author_handle}/status/{self.post_id}"