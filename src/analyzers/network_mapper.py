"""
LinkedIn network mapper for analyzing connections and expertise.
"""

import logging
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from collections import defaultdict

from sqlalchemy import String
from src.models.base import get_db
from src.models.linkedin_connection import LinkedInConnection, ExpertiseMapping
from src.models.paper import Paper

logger = logging.getLogger(__name__)


class NetworkMapper:
    """Maps and analyzes LinkedIn network for AI safety expertise."""
    
    def __init__(self):
        # Default expertise keywords
        self.expertise_keywords = {
            'ai_safety': [
                'ai safety', 'ai alignment', 'ai risk', 'existential risk',
                'x-risk', 'agi safety', 'artificial general intelligence safety'
            ],
            'alignment': [
                'alignment', 'value alignment', 'goal alignment', 'intent alignment',
                'outer alignment', 'inner alignment', 'mesa-optimization'
            ],
            'interpretability': [
                'interpretability', 'mechanistic interpretability', 'explainable ai',
                'xai', 'model interpretability', 'neural network interpretability'
            ],
            'ml_research': [
                'machine learning', 'deep learning', 'neural network', 'transformer',
                'researcher', 'research scientist', 'phd', 'professor', 'postdoc'
            ],
            'technical': [
                'engineer', 'developer', 'architect', 'technical lead', 'ml engineer',
                'ai engineer', 'data scientist', 'research engineer'
            ],
            'policy': [
                'policy', 'governance', 'regulation', 'ethics', 'ai ethics',
                'ai policy', 'tech policy', 'responsible ai'
            ],
            'control': [
                'ai control', 'control problem', 'corrigibility', 'shutdown',
                'human oversight', 'ai supervision'
            ]
        }
        
        # Company/institution weights for expertise
        self.institution_weights = {
            'deepmind': 1.5,
            'anthropic': 2.0,  # High weight for AI safety focus
            'openai': 1.3,
            'google': 1.1,
            'microsoft': 1.1,
            'meta': 1.1,
            'miri': 2.0,  # Machine Intelligence Research Institute
            'fhi': 1.8,   # Future of Humanity Institute
            'berkeley': 1.2,
            'stanford': 1.2,
            'mit': 1.2,
            'oxford': 1.2
        }
        
        # Load custom mappings from database
        self._load_expertise_mappings()
    
    def _load_expertise_mappings(self):
        """Load custom expertise mappings from database."""
        try:
            with get_db() as db:
                mappings = db.query(ExpertiseMapping).all()
                for mapping in mappings:
                    if mapping.expertise_area not in self.expertise_keywords:
                        self.expertise_keywords[mapping.expertise_area] = []
                    self.expertise_keywords[mapping.expertise_area].extend(
                        mapping.keywords or []
                    )
        except Exception as e:
            # Silently fail during tests or if tables don't exist
            logger.debug(f"Could not load expertise mappings: {e}")
    
    def analyze_network(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Analyze entire network and update expertise scores.
        
        Args:
            limit: Optional limit on connections to analyze
            
        Returns:
            Statistics about the analysis
        """
        stats = {
            "total_analyzed": 0,
            "ai_experts_found": 0,
            "interview_candidates": 0,
            "author_matches": 0,
            "errors": 0
        }
        
        with get_db() as db:
            # Get connections to analyze
            query = db.query(LinkedInConnection).filter(
                LinkedInConnection.excluded_from_analysis == False
            )
            
            if limit:
                query = query.limit(limit)
            
            connections = query.all()
            
            for connection in connections:
                try:
                    # Analyze expertise
                    expertise_tags, ai_safety_score = self._analyze_expertise(connection)
                    
                    # Calculate interview potential
                    interview_score = self._calculate_interview_potential(
                        connection, 
                        expertise_tags,
                        ai_safety_score
                    )
                    
                    # Check for author matches
                    author_matches = self._find_author_matches(connection, db)
                    
                    # Update connection
                    connection.expertise_tags = expertise_tags
                    connection.ai_safety_score = ai_safety_score
                    connection.interview_potential_score = interview_score
                    connection.matched_author_names = author_matches
                    connection.last_analyzed = datetime.utcnow()
                    
                    stats["total_analyzed"] += 1
                    
                    if ai_safety_score >= 7.0:
                        stats["ai_experts_found"] += 1
                    
                    if interview_score >= 7.5:
                        stats["interview_candidates"] += 1
                    
                    if author_matches:
                        stats["author_matches"] += 1
                    
                    # Commit every 50 records
                    if stats["total_analyzed"] % 50 == 0:
                        db.commit()
                        logger.info(f"Progress: {stats['total_analyzed']} analyzed")
                
                except Exception as e:
                    logger.error(f"Error analyzing connection {connection.id}: {e}")
                    stats["errors"] += 1
            
            # Final commit
            db.commit()
        
        logger.info(f"Network analysis complete: {stats}")
        return stats
    
    def _analyze_expertise(self, connection: LinkedInConnection) -> Tuple[List[str], float]:
        """
        Analyze connection's expertise based on position and company.
        
        Returns:
            Tuple of (expertise_tags, ai_safety_score)
        """
        expertise_tags = set()
        score = 0.0
        
        # Analyze position
        if connection.position:
            position_lower = connection.position.lower()
            for area, keywords in self.expertise_keywords.items():
                for keyword in keywords:
                    if keyword in position_lower:
                        expertise_tags.add(area)
                        score += 2.0  # Position match is strong signal
        
        # Analyze company
        if connection.company:
            company_lower = connection.company.lower()
            
            # Check for known institutions
            for institution, weight in self.institution_weights.items():
                if institution in company_lower:
                    score += 1.5 * weight
                    
                    # Add relevant tags based on company
                    if institution in ['deepmind', 'anthropic', 'openai', 'miri']:
                        expertise_tags.add('ai_safety')
                    if institution in ['anthropic', 'miri', 'fhi']:
                        expertise_tags.add('alignment')
            
            # Check for general AI/ML companies
            ai_company_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml']
            if any(keyword in company_lower for keyword in ai_company_keywords):
                score += 0.5
        
        # Check for academic positions
        academic_titles = ['professor', 'researcher', 'phd', 'postdoc', 'faculty']
        if connection.position and any(title in connection.position.lower() for title in academic_titles):
            score += 1.0
            expertise_tags.add('ml_research')
        
        # Normalize score to 0-10 range
        score = min(score, 10.0)
        
        return list(expertise_tags), score
    
    def _calculate_interview_potential(
        self,
        connection: LinkedInConnection,
        expertise_tags: List[str],
        ai_safety_score: float
    ) -> float:
        """Calculate interview potential score."""
        score = 0.0
        
        # Base score from AI safety expertise
        score += ai_safety_score * 0.4
        
        # Bonus for specific expertise
        high_value_tags = ['ai_safety', 'alignment', 'interpretability', 'control']
        matching_tags = set(expertise_tags) & set(high_value_tags)
        score += len(matching_tags) * 1.5
        
        # Position-based scoring
        if connection.position:
            position_lower = connection.position.lower()
            
            # High-value positions
            if any(term in position_lower for term in ['director', 'head', 'lead', 'principal']):
                score += 1.5
            
            # Speaking experience indicators
            if any(term in position_lower for term in ['speaker', 'evangelist', 'advocate']):
                score += 2.0
        
        # Company prestige
        if connection.company:
            company_lower = connection.company.lower()
            for institution, weight in self.institution_weights.items():
                if institution in company_lower and weight > 1.3:
                    score += 1.0
        
        # Normalize to 0-10
        return min(score, 10.0)
    
    def _find_author_matches(self, connection: LinkedInConnection, db) -> Optional[Dict]:
        """Find if connection has authored any papers."""
        if not connection.full_name:
            return None
        
        # Normalize name for matching
        name_parts = connection.full_name.lower().split()
        if len(name_parts) < 2:
            return None
        
        # Search for papers by this author
        matches = []
        
        # Try different name formats
        name_variants = [
            connection.full_name,
            f"{name_parts[-1]}, {' '.join(name_parts[:-1])}",  # Last, First
            f"{name_parts[0][0]}. {' '.join(name_parts[1:])}"  # F. Last
        ]
        
        for name_variant in name_variants:
            papers = db.query(Paper).filter(
                Paper.authors.cast(String).ilike(f'%{name_variant}%')
            ).limit(5).all()
            
            for paper in papers:
                matches.append({
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "date": paper.submission_date.isoformat() if paper.submission_date else None
                })
        
        return matches if matches else None
    
    def find_experts_by_topic(self, topic: str, limit: int = 20) -> List[LinkedInConnection]:
        """Find experts for a specific topic."""
        with get_db() as db:
            # Find connections with matching expertise
            connections = db.query(LinkedInConnection).filter(
                LinkedInConnection.expertise_tags.op('@>')([topic]),
                LinkedInConnection.ai_safety_score >= 6.0
            ).order_by(
                LinkedInConnection.ai_safety_score.desc()
            ).limit(limit).all()
            
            return connections
    
    def suggest_mentions_for_post(
        self,
        post_topic: str,
        post_keywords: List[str],
        max_mentions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Suggest relevant connections to mention in a post.
        
        Args:
            post_topic: Main topic of the post
            post_keywords: Keywords from the post
            max_mentions: Maximum mentions to suggest
            
        Returns:
            List of mention suggestions with reasons
        """
        suggestions = []
        
        with get_db() as db:
            # Find relevant experts
            query = db.query(LinkedInConnection).filter(
                LinkedInConnection.ai_safety_score >= 6.0,
                LinkedInConnection.mention_count < 5  # Avoid over-mentioning
            )
            
            # Filter by topic
            if post_topic:
                query = query.filter(
                    LinkedInConnection.expertise_tags.op('@>')([post_topic])
                )
            
            candidates = query.order_by(
                LinkedInConnection.interview_potential_score.desc()
            ).limit(max_mentions * 3).all()  # Get extra to filter
            
            # Score and rank candidates
            scored_candidates = []
            for candidate in candidates:
                score = self._score_mention_relevance(candidate, post_keywords)
                if score > 0:
                    scored_candidates.append((score, candidate))
            
            # Sort by score and take top mentions
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            
            for score, candidate in scored_candidates[:max_mentions]:
                suggestion = {
                    "name": candidate.full_name,
                    "company": candidate.company,
                    "expertise": candidate.expertise_tags,
                    "relevance_score": score,
                    "reason": self._generate_mention_reason(candidate, post_topic),
                    "connection_degree": candidate.connection_degree
                }
                suggestions.append(suggestion)
        
        return suggestions
    
    def _score_mention_relevance(
        self,
        connection: LinkedInConnection,
        keywords: List[str]
    ) -> float:
        """Score how relevant a connection is for mentioning."""
        score = 0.0
        
        # Match expertise with keywords
        if connection.expertise_tags:
            for tag in connection.expertise_tags:
                if any(keyword in tag for keyword in keywords):
                    score += 2.0
        
        # Position/company relevance
        text_to_check = f"{connection.position or ''} {connection.company or ''}".lower()
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                score += 1.0
        
        # Prefer 1st/2nd degree connections
        if connection.connection_degree == 1:
            score += 1.0
        elif connection.connection_degree == 2:
            score += 0.5
        
        # Penalize if mentioned recently
        if connection.mention_count > 2:
            score *= 0.5
        
        return score
    
    def _generate_mention_reason(
        self,
        connection: LinkedInConnection,
        topic: str
    ) -> str:
        """Generate reason for mentioning someone."""
        if 'ai_safety' in (connection.expertise_tags or []):
            return f"AI safety expert at {connection.company}"
        elif 'interpretability' in (connection.expertise_tags or []):
            return f"Working on interpretability at {connection.company}"
        elif connection.matched_author_names:
            return f"Author of relevant research"
        else:
            return f"Expert in {topic} at {connection.company}"