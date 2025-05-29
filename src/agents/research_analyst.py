"""
Research Analyst agent for analyzing papers and discussions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent
from src.models.paper import Paper
from src.models.x_post import XPost

logger = logging.getLogger(__name__)


class ResearchAnalyst(BaseAgent):
    """Agent that analyzes papers and X.com discussions for insights."""
    
    def __init__(self):
        super().__init__(
            role="Senior AI Safety Research Analyst",
            goal="Extract key insights from AI safety papers and discussions to identify breakthrough findings and important developments",
            backstory="""You are a seasoned AI safety researcher with a PhD in Machine Learning 
            and 10 years of experience analyzing technical papers. You have a keen eye for 
            identifying important breakthroughs, understanding complex technical concepts, 
            and connecting research findings to real-world implications. You're particularly 
            skilled at explaining technical concepts in accessible ways while maintaining accuracy.""",
            verbose=True
        )
    
    def get_temperature(self) -> float:
        """Use lower temperature for analytical tasks."""
        return 0.3
    
    def get_max_tokens(self) -> int:
        """Need more tokens for detailed analysis."""
        return 1000
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze papers and discussions.
        
        Args:
            context: Should contain 'papers' and/or 'posts'
            
        Returns:
            Structured research summary
        """
        papers = context.get('papers', [])
        posts = context.get('posts', [])
        
        if not papers and not posts:
            raise ValueError("No papers or posts provided for analysis")
        
        analysis = {
            "timestamp": datetime.utcnow().isoformat(),
            "papers_analyzed": len(papers),
            "posts_analyzed": len(posts),
            "key_insights": [],
            "breakthrough_findings": [],
            "connections": [],
            "content_ratings": []
        }
        
        # Analyze papers
        if papers:
            paper_insights = self._analyze_papers(papers)
            analysis["key_insights"].extend(paper_insights["insights"])
            analysis["breakthrough_findings"].extend(paper_insights["breakthroughs"])
            analysis["content_ratings"].extend(paper_insights["ratings"])
        
        # Analyze posts
        if posts:
            post_insights = self._analyze_posts(posts)
            analysis["key_insights"].extend(post_insights["insights"])
            analysis["connections"].extend(post_insights["connections"])
        
        # Connect papers to discussions
        if papers and posts:
            connections = self._connect_papers_to_discussions(papers, posts)
            analysis["connections"].extend(connections)
        
        return analysis
    
    def _analyze_papers(self, papers: List[Paper]) -> Dict[str, List]:
        """Analyze academic papers for insights."""
        insights = []
        breakthroughs = []
        ratings = []
        
        for paper in papers[:5]:  # Analyze top 5 papers
            prompt = f"""Analyze this AI safety paper and extract key insights:

Title: {paper.title}
Authors: {', '.join([a.get('name', '') for a in paper.authors[:3]])}
Abstract: {paper.abstract[:1000]}...

Please provide:
1. Main contribution (2-3 sentences)
2. Key technical innovation (if any)
3. Relevance to AI safety/control/interpretability
4. Potential real-world impact
5. Content potential rating (1-10) for LinkedIn post
6. One surprising or counterintuitive finding (if any)

Format your response as a structured analysis."""

            try:
                response = self.llm_config.complete(
                    messages=[
                        {"role": "system", "content": self.backstory},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.get_temperature(),
                    max_tokens=self.get_max_tokens()
                )
                
                analysis = response.choices[0].message.content
                
                # Parse and structure the analysis
                insights.append({
                    "paper_id": paper.arxiv_id,
                    "title": paper.title,
                    "analysis": analysis,
                    "relevance_score": paper.relevance_score
                })
                
                # Extract rating (simple parsing)
                if "rating:" in analysis.lower():
                    try:
                        rating_text = analysis.lower().split("rating:")[1].split()[0]
                        rating = float(rating_text.strip().replace("/10", ""))
                        ratings.append({
                            "paper_id": paper.arxiv_id,
                            "rating": rating,
                            "title": paper.title
                        })
                    except:
                        pass
                
                # Check for breakthrough findings
                if any(word in analysis.lower() for word in ["breakthrough", "novel", "first", "revolutionary"]):
                    breakthroughs.append({
                        "paper_id": paper.arxiv_id,
                        "title": paper.title,
                        "finding": analysis
                    })
                    
            except Exception as e:
                logger.error(f"Error analyzing paper {paper.arxiv_id}: {e}")
        
        return {
            "insights": insights,
            "breakthroughs": breakthroughs,
            "ratings": sorted(ratings, key=lambda x: x['rating'], reverse=True)
        }
    
    def _analyze_posts(self, posts: List[XPost]) -> Dict[str, List]:
        """Analyze X.com posts for insights and trends."""
        insights = []
        connections = []
        
        # Group posts by topic/thread
        viral_posts = [p for p in posts if p.is_viral]
        arxiv_posts = [p for p in posts if p.arxiv_refs]
        
        # Analyze viral discussions
        if viral_posts:
            prompt = f"""Analyze these viral AI safety discussions from X.com:

{self._format_posts_for_analysis(viral_posts[:5])}

Identify:
1. Main themes and concerns
2. Points of controversy or debate
3. Emerging trends or topics
4. Key questions being asked
5. Overall sentiment and tone"""

            try:
                response = self.llm_config.complete(
                    messages=[
                        {"role": "system", "content": self.backstory},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.get_temperature(),
                    max_tokens=self.get_max_tokens()
                )
                
                insights.append({
                    "type": "viral_discussions",
                    "analysis": response.choices[0].message.content,
                    "post_count": len(viral_posts)
                })
                
            except Exception as e:
                logger.error(f"Error analyzing viral posts: {e}")
        
        # Analyze posts mentioning papers
        if arxiv_posts:
            for post in arxiv_posts[:10]:
                connections.append({
                    "post_id": post.post_id,
                    "author": post.author_handle,
                    "arxiv_refs": post.arxiv_refs,
                    "engagement": post.engagement_score,
                    "content_preview": post.content[:200]
                })
        
        return {
            "insights": insights,
            "connections": connections
        }
    
    def _connect_papers_to_discussions(self, papers: List[Paper], posts: List[XPost]) -> List[Dict]:
        """Find connections between papers and social discussions."""
        connections = []
        
        # Create mapping of arxiv IDs to papers
        paper_map = {p.arxiv_id: p for p in papers}
        
        # Find posts discussing papers
        for post in posts:
            if post.arxiv_refs:
                for arxiv_id in post.arxiv_refs:
                    if arxiv_id in paper_map:
                        connections.append({
                            "paper_id": arxiv_id,
                            "paper_title": paper_map[arxiv_id].title,
                            "post_id": post.post_id,
                            "post_author": post.author_handle,
                            "post_engagement": post.engagement_score,
                            "discussion_preview": post.content[:200]
                        })
        
        return connections
    
    def _format_posts_for_analysis(self, posts: List[XPost]) -> str:
        """Format posts for LLM analysis."""
        formatted = []
        for i, post in enumerate(posts, 1):
            formatted.append(f"""Post {i}:
Author: @{post.author_handle} ({post.likes} likes, {post.retweets} retweets)
Content: {post.content}
---""")
        return "\n".join(formatted)