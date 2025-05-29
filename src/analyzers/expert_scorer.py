"""
Expert scoring algorithm for LinkedIn connections.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from src.models.base import get_db
from src.models.linkedin_connection import LinkedInConnection
from src.models.paper import Paper
from src.models.x_post import XPost

logger = logging.getLogger(__name__)


class ExpertScorer:
    """Scores LinkedIn connections for expertise and interview potential."""
    
    def __init__(self):
        # Scoring weights
        self.weights = {
            'position_relevance': 0.25,
            'company_prestige': 0.20,
            'publication_record': 0.20,
            'social_activity': 0.15,
            'speaking_experience': 0.10,
            'network_influence': 0.10
        }
        
        # Position keywords and scores
        self.position_scores = {
            'researcher': 8,
            'scientist': 8,
            'professor': 9,
            'phd': 7,
            'postdoc': 7,
            'engineer': 6,
            'director': 8,
            'head': 8,
            'lead': 7,
            'founder': 8,
            'cto': 7,
            'safety': 9,
            'alignment': 9,
            'interpretability': 9,
            'ethics': 7,
            'policy': 6
        }
        
        # Speaking experience indicators
        self.speaking_indicators = [
            'speaker', 'evangelist', 'advocate', 'presenter',
            'ted', 'keynote', 'panelist', 'moderator'
        ]
    
    def score_expert(self, connection: LinkedInConnection) -> Dict[str, float]:
        """
        Calculate comprehensive expert scores.
        
        Args:
            connection: LinkedIn connection to score
            
        Returns:
            Dictionary with component scores and final scores
        """
        scores = {}
        
        # Calculate component scores
        scores['position_relevance'] = self._score_position_relevance(connection)
        scores['company_prestige'] = self._score_company_prestige(connection)
        scores['publication_record'] = self._score_publication_record(connection)
        scores['social_activity'] = self._score_social_activity(connection)
        scores['speaking_experience'] = self._score_speaking_experience(connection)
        scores['network_influence'] = self._score_network_influence(connection)
        
        # Calculate weighted final scores
        ai_safety_score = sum(
            scores[component] * self.weights[component]
            for component in self.weights
        )
        
        # Interview potential includes additional factors
        interview_score = self._calculate_interview_potential(scores, connection)
        
        # Mention relevance score
        mention_score = self._calculate_mention_relevance(scores, connection)
        
        return {
            'component_scores': scores,
            'ai_safety_score': min(ai_safety_score, 10.0),
            'interview_potential_score': min(interview_score, 10.0),
            'mention_relevance_score': min(mention_score, 10.0)
        }
    
    def _score_position_relevance(self, connection: LinkedInConnection) -> float:
        """Score based on position title relevance."""
        if not connection.position:
            return 0.0
        
        position_lower = connection.position.lower()
        score = 0.0
        
        # Check for keyword matches
        for keyword, keyword_score in self.position_scores.items():
            if keyword in position_lower:
                score = max(score, keyword_score)
        
        # Bonus for senior positions
        if any(term in position_lower for term in ['senior', 'principal', 'staff']):
            score += 1.0
        
        # Academic bonus
        if any(term in position_lower for term in ['professor', 'faculty', 'academic']):
            score += 0.5
        
        return min(score, 10.0)
    
    def _score_company_prestige(self, connection: LinkedInConnection) -> float:
        """Score based on company/institution prestige."""
        if not connection.company:
            return 0.0
        
        company_lower = connection.company.lower()
        
        # Top tier AI safety organizations
        if any(org in company_lower for org in ['anthropic', 'miri', 'fhi']):
            return 10.0
        
        # Major AI labs
        if any(org in company_lower for org in ['deepmind', 'openai', 'google brain']):
            return 9.0
        
        # Tech giants with AI research
        if any(org in company_lower for org in ['google', 'microsoft', 'meta', 'apple']):
            return 7.0
        
        # Top universities
        top_universities = [
            'stanford', 'mit', 'berkeley', 'oxford', 'cambridge',
            'harvard', 'cmu', 'caltech', 'eth zurich'
        ]
        if any(uni in company_lower for uni in top_universities):
            return 8.0
        
        # Other universities
        if any(term in company_lower for term in ['university', 'institute', 'college']):
            return 5.0
        
        # AI/ML companies
        if any(term in company_lower for term in ['ai', 'artificial intelligence', 'machine learning']):
            return 6.0
        
        return 3.0  # Default for other companies
    
    def _score_publication_record(self, connection: LinkedInConnection) -> float:
        """Score based on publication record."""
        score = 0.0
        
        # Check matched papers
        if connection.matched_author_names:
            num_papers = len(connection.matched_author_names)
            
            # Base score for having publications
            score = min(5.0 + (num_papers * 1.5), 10.0)
            
            # Check paper quality (would need to query papers)
            try:
                with get_db() as db:
                    for paper_info in connection.matched_author_names[:5]:
                        paper = db.query(Paper).filter_by(
                            arxiv_id=paper_info.get('arxiv_id')
                        ).first()
                        
                        if paper and paper.relevance_score >= 0.8:
                            score += 0.5
            except Exception:
                # Skip paper quality check if table doesn't exist
                pass
        
        return min(score, 10.0)
    
    def _score_social_activity(self, connection: LinkedInConnection) -> float:
        """Score based on social media activity about AI."""
        score = 0.0
        
        # LinkedIn posts about AI
        if connection.posts_about_ai:
            score = min(3.0 + (connection.posts_about_ai * 0.5), 7.0)
        
        # Check if they have matching X.com handle
        if connection.matched_social_handles:
            score += 2.0
            
            # Could query X posts for more detailed scoring
            try:
                with get_db() as db:
                    for handle_info in connection.matched_social_handles[:1]:
                        handle = handle_info.get('handle')
                        if handle:
                            viral_posts = db.query(XPost).filter(
                                XPost.author_handle == handle,
                                XPost.is_viral == True
                            ).count()
                            
                            if viral_posts > 0:
                                score += min(viral_posts * 0.5, 3.0)
            except Exception:
                # Skip X post check if table doesn't exist
                pass
        
        return min(score, 10.0)
    
    def _score_speaking_experience(self, connection: LinkedInConnection) -> float:
        """Score based on speaking/presentation experience."""
        score = 0.0
        
        if connection.position:
            position_lower = connection.position.lower()
            
            # Check for speaking indicators
            for indicator in self.speaking_indicators:
                if indicator in position_lower:
                    score = 8.0
                    break
            
            # Conference/event mentions
            if any(term in position_lower for term in ['conference', 'summit', 'symposium']):
                score = max(score, 6.0)
        
        # Podcast experience (from bio/position)
        if connection.position and 'podcast' in connection.position.lower():
            score = max(score, 7.0)
        
        return score
    
    def _score_network_influence(self, connection: LinkedInConnection) -> float:
        """Score based on network influence."""
        score = 5.0  # Base score
        
        # Mutual connections (indicator of network centrality)
        if connection.mutual_connections:
            if connection.mutual_connections > 50:
                score += 3.0
            elif connection.mutual_connections > 20:
                score += 2.0
            elif connection.mutual_connections > 10:
                score += 1.0
        
        # Connection degree
        if connection.connection_degree == 1:
            score += 1.0  # Direct connections have more influence
        
        # Verified expert status
        if connection.is_verified_expert:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_interview_potential(
        self,
        scores: Dict[str, float],
        connection: LinkedInConnection
    ) -> float:
        """Calculate interview potential with additional factors."""
        # Start with weighted average
        base_score = sum(
            scores[component] * self.weights[component]
            for component in self.weights
        )
        
        # Boost for speaking experience
        base_score += scores['speaking_experience'] * 0.2
        
        # Boost for high publication + speaking combo
        if scores['publication_record'] >= 7 and scores['speaking_experience'] >= 6:
            base_score += 1.0
        
        # Slight penalty for no social presence
        if scores['social_activity'] < 2:
            base_score *= 0.9
        
        return base_score
    
    def _calculate_mention_relevance(
        self,
        scores: Dict[str, float],
        connection: LinkedInConnection
    ) -> float:
        """Calculate how relevant someone is for mentioning in posts."""
        # Different weights for mention relevance
        mention_weights = {
            'position_relevance': 0.3,
            'company_prestige': 0.2,
            'network_influence': 0.25,
            'social_activity': 0.25
        }
        
        score = sum(
            scores.get(component, 0) * weight
            for component, weight in mention_weights.items()
        )
        
        # Boost for 1st degree connections
        if connection.connection_degree == 1:
            score += 1.0
        
        # Penalty for over-mentioning
        mention_count = connection.mention_count or 0
        if mention_count > 3:
            score *= 0.7
        elif mention_count > 5:
            score *= 0.5
        
        return score
    
    def update_connection_scores(self, connection_id: int) -> Dict[str, float]:
        """Update scores for a specific connection."""
        with get_db() as db:
            connection = db.query(LinkedInConnection).filter_by(id=connection_id).first()
            
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            # Calculate scores
            results = self.score_expert(connection)
            
            # Update connection
            connection.ai_safety_score = results['ai_safety_score']
            connection.interview_potential_score = results['interview_potential_score']
            connection.mention_relevance_score = results['mention_relevance_score']
            connection.last_analyzed = datetime.utcnow()
            
            db.commit()
            
            return results
    
    def batch_update_scores(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Update scores for multiple connections."""
        stats = {
            'updated': 0,
            'errors': 0
        }
        
        with get_db() as db:
            # Get connections needing update
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = db.query(LinkedInConnection).filter(
                (LinkedInConnection.last_analyzed == None) |
                (LinkedInConnection.last_analyzed < week_ago)
            )
            
            if limit:
                query = query.limit(limit)
            
            connections = query.all()
            
            for connection in connections:
                try:
                    results = self.score_expert(connection)
                    
                    connection.ai_safety_score = results['ai_safety_score']
                    connection.interview_potential_score = results['interview_potential_score']
                    connection.mention_relevance_score = results['mention_relevance_score']
                    connection.last_analyzed = datetime.utcnow()
                    
                    stats['updated'] += 1
                    
                    if stats['updated'] % 50 == 0:
                        db.commit()
                        logger.info(f"Updated {stats['updated']} connections")
                
                except Exception as e:
                    logger.error(f"Error scoring connection {connection.id}: {e}")
                    stats['errors'] += 1
            
            db.commit()
        
        return stats