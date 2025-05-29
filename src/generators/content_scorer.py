"""
Content scoring system for ranking and prioritizing content opportunities.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.models.base import get_db
from src.models.paper import Paper
from src.models.x_post import XPost
from src.models.linkedin_connection import LinkedInConnection

logger = logging.getLogger(__name__)


@dataclass
class ContentOpportunity:
    """Represents a content creation opportunity."""
    
    content_type: str  # 'paper', 'x_discussion', 'trend_analysis'
    source_id: int
    title: str
    description: str
    
    # Scoring components
    novelty_score: float
    relevance_score: float
    timeliness_score: float
    engagement_potential: float
    visual_potential: float
    
    # Overall score
    total_score: float
    
    # Metadata
    source_data: dict
    recommended_angle: str
    suggested_mentions: List[str]
    
    def __post_init__(self):
        """Calculate total score if not provided."""
        if not hasattr(self, 'total_score') or self.total_score == 0:
            self.total_score = self._calculate_total_score()
    
    def _calculate_total_score(self) -> float:
        """Calculate weighted total score."""
        weights = {
            'novelty': 0.25,
            'relevance': 0.30,
            'timeliness': 0.20,
            'engagement': 0.15,
            'visual': 0.10
        }
        
        return (
            self.novelty_score * weights['novelty'] +
            self.relevance_score * weights['relevance'] +
            self.timeliness_score * weights['timeliness'] +
            self.engagement_potential * weights['engagement'] +
            self.visual_potential * weights['visual']
        )


class ContentScorer:
    """Scores and ranks content opportunities for post generation."""
    
    def __init__(self):
        self.novelty_keywords = [
            'novel', 'new', 'breakthrough', 'first', 'unprecedented',
            'revolutionary', 'innovative', 'cutting-edge', 'state-of-the-art'
        ]
        
        self.high_relevance_topics = [
            'ai safety', 'ai alignment', 'mechanistic interpretability',
            'ai control', 'existential risk', 'ai governance',
            'interpretability', 'safety', 'alignment', 'control'
        ]
        
        self.engagement_indicators = [
            'controversial', 'surprising', 'implications',
            'breakthrough', 'concerns', 'debate', 'discussion'
        ]
    
    def score_recent_content(self, days: int = 7) -> List[ContentOpportunity]:
        """Score all recent content and return ranked opportunities."""
        opportunities = []
        
        # Score recent papers
        paper_opportunities = self._score_papers(days)
        opportunities.extend(paper_opportunities)
        
        # Score X.com discussions
        x_opportunities = self._score_x_discussions(days)
        opportunities.extend(x_opportunities)
        
        # Score trending combinations
        trend_opportunities = self._score_trend_combinations(days)
        opportunities.extend(trend_opportunities)
        
        # Sort by total score
        opportunities.sort(key=lambda x: x.total_score, reverse=True)
        
        logger.info(f"Scored {len(opportunities)} content opportunities")
        return opportunities
    
    def _score_papers(self, days: int) -> List[ContentOpportunity]:
        """Score recent papers for content potential."""
        opportunities = []
        
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            papers = db.query(Paper).filter(
                Paper.submission_date >= cutoff_date,
                Paper.relevance_score >= 0.6
            ).order_by(Paper.submission_date.desc()).limit(50).all()
            
            for paper in papers:
                opportunity = self._score_paper(paper)
                if opportunity.total_score >= 6.0:  # Minimum threshold
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _score_paper(self, paper: Paper) -> ContentOpportunity:
        """Score individual paper for content potential."""
        # Novelty score
        novelty = self._calculate_novelty_score(paper)
        
        # Relevance score (use existing paper relevance)
        relevance = min(paper.relevance_score * 10, 10.0)
        
        # Timeliness score
        timeliness = self._calculate_timeliness_score(paper.submission_date)
        
        # Engagement potential
        engagement = self._calculate_engagement_potential(paper)
        
        # Visual potential
        visual = self._calculate_visual_potential(paper)
        
        # Generate recommended angle
        angle = self._generate_paper_angle(paper)
        
        # Suggest mentions
        mentions = self._suggest_paper_mentions(paper)
        
        return ContentOpportunity(
            content_type='paper',
            source_id=paper.id,
            title=paper.title,
            description=f"arXiv paper: {paper.arxiv_id}",
            novelty_score=novelty,
            relevance_score=relevance,
            timeliness_score=timeliness,
            engagement_potential=engagement,
            visual_potential=visual,
            total_score=0,  # Will be calculated in __post_init__
            source_data={
                'arxiv_id': paper.arxiv_id,
                'authors': paper.authors,
                'abstract': paper.abstract[:200] + '...' if paper.abstract else '',
                'categories': paper.categories
            },
            recommended_angle=angle,
            suggested_mentions=mentions
        )
    
    def _score_x_discussions(self, days: int) -> List[ContentOpportunity]:
        """Score X.com discussions for content potential."""
        opportunities = []
        
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find viral or highly relevant posts
            x_posts = db.query(XPost).filter(
                XPost.created_at >= cutoff_date,
                (XPost.is_viral == True) | (XPost.relevance_score >= 0.8)
            ).order_by(XPost.created_at.desc()).limit(30).all()
            
            for post in x_posts:
                opportunity = self._score_x_post(post)
                if opportunity.total_score >= 5.5:  # Lower threshold for discussions
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _score_x_post(self, post: XPost) -> ContentOpportunity:
        """Score individual X post for content potential."""
        # Novelty based on uniqueness of discussion
        novelty = 7.0 if post.is_viral else 5.0
        
        # Relevance (use existing relevance score)
        relevance = min(post.relevance_score * 10, 10.0)
        
        # Timeliness 
        timeliness = self._calculate_timeliness_score(post.created_at)
        
        # Engagement potential (viral posts have high potential)
        engagement = 9.0 if post.is_viral else 6.0
        
        # Visual potential (lower for text discussions)
        visual = 4.0
        
        # Generate angle
        angle = self._generate_discussion_angle(post)
        
        # Suggest mentions
        mentions = self._suggest_discussion_mentions(post)
        
        return ContentOpportunity(
            content_type='x_discussion',
            source_id=post.id,
            title=f"Discussion: {post.content[:50]}...",
            description=f"X.com discussion by @{post.author_handle}",
            novelty_score=novelty,
            relevance_score=relevance,
            timeliness_score=timeliness,
            engagement_potential=engagement,
            visual_potential=visual,
            total_score=0,
            source_data={
                'content': post.content,
                'author_handle': post.author_handle,
                'is_viral': post.is_viral,
                'arxiv_references': post.arxiv_references
            },
            recommended_angle=angle,
            suggested_mentions=mentions
        )
    
    def _score_trend_combinations(self, days: int) -> List[ContentOpportunity]:
        """Score combinations of papers and discussions for trend analysis."""
        opportunities = []
        
        # Look for papers with related X discussions
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find papers with X post references
            papers_with_discussions = db.query(Paper).filter(
                Paper.submission_date >= cutoff_date,
                Paper.mentioned_in_posts.is_not(None),
                Paper.mentioned_in_posts != []
            ).limit(10).all()
            
            for paper in papers_with_discussions:
                opportunity = self._score_trend_combination(paper)
                if opportunity.total_score >= 7.0:  # Higher threshold for trends
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _score_trend_combination(self, paper: Paper) -> ContentOpportunity:
        """Score paper + discussion combination."""
        # High novelty for trending combinations
        novelty = 8.5
        
        # High relevance if both paper and discussions are relevant
        relevance = min(paper.relevance_score * 10, 10.0)
        
        # Good timeliness
        timeliness = self._calculate_timeliness_score(paper.submission_date)
        
        # Very high engagement potential
        engagement = 9.0
        
        # Good visual potential (can combine figures + quotes)
        visual = 7.5
        
        angle = self._generate_trend_angle(paper)
        mentions = self._suggest_trend_mentions(paper)
        
        return ContentOpportunity(
            content_type='trend_analysis',
            source_id=paper.id,
            title=f"Trend: {paper.title[:50]}...",
            description=f"Trending discussion around {paper.arxiv_id}",
            novelty_score=novelty,
            relevance_score=relevance,
            timeliness_score=timeliness,
            engagement_potential=engagement,
            visual_potential=visual,
            total_score=0,
            source_data={
                'paper': {
                    'arxiv_id': paper.arxiv_id,
                    'title': paper.title,
                    'authors': paper.authors
                },
                'discussion_count': len(paper.mentioned_in_posts or [])
            },
            recommended_angle=angle,
            suggested_mentions=mentions
        )
    
    def _calculate_novelty_score(self, paper: Paper) -> float:
        """Calculate novelty score based on paper content."""
        score = 5.0  # Base score
        
        text_to_check = f"{paper.title} {paper.abstract or ''}".lower()
        
        # Check for novelty keywords
        for keyword in self.novelty_keywords:
            if keyword in text_to_check:
                score += 1.0
        
        # Boost for very recent papers
        days_old = (datetime.utcnow() - paper.submission_date).days
        if days_old <= 1:
            score += 2.0
        elif days_old <= 3:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_timeliness_score(self, date: datetime) -> float:
        """Calculate timeliness score based on recency."""
        days_old = (datetime.utcnow() - date).days
        
        if days_old == 0:
            return 10.0
        elif days_old <= 1:
            return 9.0
        elif days_old <= 3:
            return 7.0
        elif days_old <= 7:
            return 5.0
        else:
            return max(10.0 - days_old, 1.0)
    
    def _calculate_engagement_potential(self, paper: Paper) -> float:
        """Calculate engagement potential based on content characteristics."""
        score = 5.0
        
        text_to_check = f"{paper.title} {paper.abstract or ''}".lower()
        
        # Check for engagement indicators
        for indicator in self.engagement_indicators:
            if indicator in text_to_check:
                score += 1.0
        
        # Boost for high relevance
        if paper.relevance_score >= 0.9:
            score += 1.5
        
        return min(score, 10.0)
    
    def _calculate_visual_potential(self, paper: Paper) -> float:
        """Calculate visual content potential."""
        score = 3.0  # Base score for papers (usually have figures)
        
        # Boost for certain types of papers
        if paper.categories:
            visual_categories = ['cs.CV', 'cs.LG', 'cs.AI']
            for category in visual_categories:
                if category in paper.categories:
                    score += 2.0
                    break
        
        # Check for figure-heavy papers
        if paper.abstract:
            visual_keywords = ['figure', 'visualization', 'chart', 'graph', 'plot']
            for keyword in visual_keywords:
                if keyword in paper.abstract.lower():
                    score += 1.0
        
        return min(score, 10.0)
    
    def _generate_paper_angle(self, paper: Paper) -> str:
        """Generate recommended content angle for paper."""
        angles = [
            f"New insights on {self._extract_main_topic(paper)}",
            f"Practical implications of {paper.title[:50]}...",
            f"What this means for AI safety research",
            f"Breaking down the methodology in {paper.arxiv_id}",
            f"Future directions inspired by this work"
        ]
        
        # Simple selection based on paper characteristics
        if 'safety' in paper.title.lower():
            return angles[2]
        elif 'method' in paper.title.lower():
            return angles[3]
        else:
            return angles[0]
    
    def _generate_discussion_angle(self, post: XPost) -> str:
        """Generate recommended angle for X discussion."""
        return f"Community perspectives on {self._extract_discussion_topic(post)}"
    
    def _generate_trend_angle(self, paper: Paper) -> str:
        """Generate angle for trending combination."""
        return f"Why everyone is talking about {self._extract_main_topic(paper)}"
    
    def _extract_main_topic(self, paper: Paper) -> str:
        """Extract main topic from paper."""
        title_lower = paper.title.lower()
        
        for topic in self.high_relevance_topics:
            if topic in title_lower:
                return topic
        
        # Fallback to first few words
        words = paper.title.split()[:3]
        return ' '.join(words).lower()
    
    def _extract_discussion_topic(self, post: XPost) -> str:
        """Extract main topic from X discussion."""
        content_lower = post.content.lower()
        
        for topic in self.high_relevance_topics:
            if topic in content_lower:
                return topic
        
        return "AI research"
    
    def _suggest_paper_mentions(self, paper: Paper) -> List[str]:
        """Suggest relevant mentions for paper post."""
        mentions = []
        
        # Would integrate with network analyzer to find relevant experts
        # For now, return empty list
        return mentions
    
    def _suggest_discussion_mentions(self, post: XPost) -> List[str]:
        """Suggest mentions for discussion post."""
        mentions = []
        
        # Could mention the original author if they're in network
        if post.author_handle:
            mentions.append(f"@{post.author_handle}")
        
        return mentions
    
    def _suggest_trend_mentions(self, paper: Paper) -> List[str]:
        """Suggest mentions for trending content."""
        mentions = []
        
        # Could mention paper authors if they're in network
        # Would integrate with network analyzer
        return mentions
    
    def get_top_opportunities(self, count: int = 3, days: int = 7) -> List[ContentOpportunity]:
        """Get top content opportunities for the specified period."""
        all_opportunities = self.score_recent_content(days)
        
        # Ensure diversity in types
        selected = []
        type_counts = {'paper': 0, 'x_discussion': 0, 'trend_analysis': 0}
        max_per_type = max(1, count // 2)
        
        for opportunity in all_opportunities:
            if len(selected) >= count:
                break
            
            if type_counts[opportunity.content_type] < max_per_type:
                selected.append(opportunity)
                type_counts[opportunity.content_type] += 1
        
        # Fill remaining slots with best regardless of type
        remaining = count - len(selected)
        for opportunity in all_opportunities:
            if remaining <= 0:
                break
            if opportunity not in selected:
                selected.append(opportunity)
                remaining -= 1
        
        return selected[:count]