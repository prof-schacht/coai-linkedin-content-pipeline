"""
Interview Scout agent for identifying podcast candidates.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent
from src.models.paper import Paper
from src.models.x_post import XPost

logger = logging.getLogger(__name__)


class InterviewScout(BaseAgent):
    """Agent that identifies and evaluates potential podcast interview candidates."""
    
    def __init__(self):
        super().__init__(
            role="Podcast Talent Scout & Network Analyst",
            goal="Identify and evaluate AI safety researchers and thought leaders who would make excellent podcast guests",
            backstory="""You are a podcast producer with expertise in AI and technology. 
            You have 6 years of experience identifying compelling speakers who can explain 
            complex topics in accessible ways. You understand what makes a great podcast 
            guest: expertise, communication skills, unique perspectives, and the ability 
            to engage audiences. You're skilled at evaluating someone's communication style 
            from their writing and assessing their potential reach and influence.""",
            verbose=True
        )
        
        # Evaluation criteria weights
        self.criteria_weights = {
            "expertise": 0.25,
            "communication": 0.25,
            "relevance": 0.20,
            "reach": 0.15,
            "uniqueness": 0.15
        }
    
    def get_temperature(self) -> float:
        """Lower temperature for analytical evaluation."""
        return 0.4
    
    def get_max_tokens(self) -> int:
        """Moderate tokens for candidate evaluation."""
        return 700
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify and evaluate potential interview candidates.
        
        Args:
            context: Should contain papers, posts, and optionally network_data
            
        Returns:
            Ranked list of interview candidates
        """
        papers = context.get('papers', [])
        posts = context.get('posts', [])
        network_data = context.get('network_data', {})
        
        # Extract candidates from various sources
        candidates = self._extract_candidates(papers, posts)
        
        # Evaluate each candidate
        evaluated_candidates = []
        for candidate in candidates:
            evaluation = self._evaluate_candidate(candidate, network_data)
            evaluated_candidates.append(evaluation)
        
        # Rank candidates
        ranked_candidates = self._rank_candidates(evaluated_candidates)
        
        # Generate outreach strategies
        top_candidates = ranked_candidates[:5]
        for candidate in top_candidates:
            candidate['outreach_strategy'] = self._generate_outreach_strategy(
                candidate, 
                network_data
            )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_candidates": len(candidates),
            "evaluated_candidates": len(evaluated_candidates),
            "top_candidates": top_candidates,
            "evaluation_criteria": self.criteria_weights
        }
    
    def _extract_candidates(
        self, 
        papers: List[Paper], 
        posts: List[XPost]
    ) -> List[Dict[str, Any]]:
        """Extract potential candidates from papers and posts."""
        candidates = {}
        
        # Extract from papers
        for paper in papers:
            if paper.relevance_score >= 0.6:
                for author in paper.authors[:3]:  # Top 3 authors
                    author_name = author.get('name', '')
                    if author_name and author_name not in candidates:
                        candidates[author_name] = {
                            "name": author_name,
                            "source": "research_paper",
                            "papers": [paper.arxiv_id],
                            "paper_titles": [paper.title],
                            "expertise_areas": paper.keyword_matches or [],
                            "recent_work": paper.submission_date
                        }
                    elif author_name in candidates:
                        candidates[author_name]["papers"].append(paper.arxiv_id)
                        candidates[author_name]["paper_titles"].append(paper.title)
        
        # Extract from viral posts
        for post in posts:
            if post.is_viral and post.relevance_score >= 0.6:
                author = f"@{post.author_handle}"
                if author not in candidates:
                    candidates[author] = {
                        "name": post.author_name or author,
                        "handle": post.author_handle,
                        "source": "social_media",
                        "viral_posts": [post.post_id],
                        "total_engagement": post.engagement_score,
                        "expertise_areas": post.hashtags or [],
                        "recent_activity": post.posted_at
                    }
                else:
                    if "viral_posts" not in candidates[author]:
                        candidates[author]["viral_posts"] = []
                    candidates[author]["viral_posts"].append(post.post_id)
                    candidates[author]["total_engagement"] = candidates[author].get(
                        "total_engagement", 0
                    ) + post.engagement_score
        
        return list(candidates.values())
    
    def _evaluate_candidate(
        self, 
        candidate: Dict[str, Any], 
        network_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a single candidate."""
        # Prepare evaluation context
        eval_context = f"""Evaluate this potential podcast guest for an AI safety podcast:

Candidate: {candidate['name']}
Source: {candidate['source']}

{self._format_candidate_details(candidate)}

Please evaluate on these criteria (1-10 scale):
1. Expertise: Depth of knowledge in AI safety/control/interpretability
2. Communication: Ability to explain complex topics clearly
3. Relevance: How current and important their work is
4. Reach: Potential audience and influence
5. Uniqueness: Unique perspective or controversial takes

Provide:
- Score for each criterion (1-10)
- Overall recommendation (strong yes/yes/maybe/no)
- Key talking points they could discuss
- Potential concerns or challenges
- What makes them unique"""

        try:
            response = self.llm_config.complete(
                messages=[
                    {"role": "system", "content": self.backstory},
                    {"role": "user", "content": eval_context}
                ],
                temperature=self.get_temperature(),
                max_tokens=self.get_max_tokens()
            )
            
            evaluation_text = response.choices[0].message.content
            
            # Parse scores (simplified - in production would use structured output)
            scores = self._parse_evaluation_scores(evaluation_text)
            
            # Calculate weighted score
            weighted_score = sum(
                scores.get(criterion, 5) * weight 
                for criterion, weight in self.criteria_weights.items()
            )
            
            # Check network proximity
            connection_degree = self._check_network_connection(candidate, network_data)
            
            return {
                **candidate,
                "evaluation": evaluation_text,
                "scores": scores,
                "weighted_score": weighted_score,
                "connection_degree": connection_degree,
                "recommendation": self._get_recommendation(weighted_score)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating candidate {candidate['name']}: {e}")
            return {
                **candidate,
                "evaluation": "Error in evaluation",
                "scores": {},
                "weighted_score": 0,
                "error": str(e)
            }
    
    def _format_candidate_details(self, candidate: Dict[str, Any]) -> str:
        """Format candidate details for evaluation."""
        details = []
        
        if "papers" in candidate:
            details.append(f"Research Papers: {len(candidate['papers'])}")
            details.append(f"Recent Paper: {candidate['paper_titles'][0][:100]}...")
        
        if "viral_posts" in candidate:
            details.append(f"Viral Posts: {len(candidate['viral_posts'])}")
            details.append(f"Total Engagement: {candidate.get('total_engagement', 0)}")
        
        if "expertise_areas" in candidate:
            areas = ", ".join(candidate['expertise_areas'][:5])
            details.append(f"Expertise Areas: {areas}")
        
        return "\n".join(details)
    
    def _parse_evaluation_scores(self, evaluation_text: str) -> Dict[str, float]:
        """Parse numerical scores from evaluation text."""
        scores = {}
        criteria = ["expertise", "communication", "relevance", "reach", "uniqueness"]
        
        for criterion in criteria:
            # Simple pattern matching - would be more robust in production
            import re
            pattern = f"{criterion}.*?(\\d+(\\.\\d+)?)/10"
            match = re.search(pattern, evaluation_text.lower())
            if match:
                scores[criterion] = float(match.group(1))
            else:
                scores[criterion] = 5.0  # Default middle score
        
        return scores
    
    def _check_network_connection(
        self, 
        candidate: Dict[str, Any], 
        network_data: Dict[str, Any]
    ) -> int:
        """Check connection degree in LinkedIn network."""
        # Placeholder - would integrate with actual LinkedIn data
        # Return connection degree: 1 (direct), 2 (second), 3 (third), 0 (none)
        
        if not network_data:
            return 0
        
        # Simulate connection checking
        handle = candidate.get('handle', candidate.get('name', '').lower().replace(' ', ''))
        
        if handle in network_data.get('direct_connections', []):
            return 1
        elif handle in network_data.get('second_connections', []):
            return 2
        elif handle in network_data.get('third_connections', []):
            return 3
        else:
            return 0
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on weighted score."""
        if score >= 8:
            return "strong_yes"
        elif score >= 6.5:
            return "yes"
        elif score >= 5:
            return "maybe"
        else:
            return "no"
    
    def _rank_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank candidates by multiple factors."""
        # Sort by weighted score, then by connection degree
        ranked = sorted(
            candidates,
            key=lambda x: (
                x.get('weighted_score', 0),
                -x.get('connection_degree', 3)  # Negative for ascending
            ),
            reverse=True
        )
        
        # Add ranking
        for i, candidate in enumerate(ranked, 1):
            candidate['rank'] = i
        
        return ranked
    
    def _generate_outreach_strategy(
        self, 
        candidate: Dict[str, Any], 
        network_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate personalized outreach strategy."""
        connection_degree = candidate.get('connection_degree', 0)
        
        if connection_degree == 1:
            approach = "direct_message"
            intro = "Hi [Name], we've connected before..."
        elif connection_degree == 2:
            approach = "mutual_introduction"
            intro = "Hi [Name], our mutual connection [Mutual] suggested..."
        else:
            approach = "cold_outreach"
            intro = "Hi [Name], I've been following your work on..."
        
        talking_points = []
        if "paper_titles" in candidate:
            talking_points.append(f"Your recent paper on {candidate['paper_titles'][0][:50]}...")
        if candidate.get('source') == 'social_media':
            talking_points.append("Your insights on X.com about AI safety")
        
        return {
            "approach": approach,
            "intro_template": intro,
            "talking_points": talking_points,
            "best_channel": "LinkedIn" if connection_degree <= 2 else "Email",
            "personalization_tips": [
                "Reference their recent work",
                "Mention specific insights you found valuable",
                "Connect to COAI Research mission"
            ]
        }