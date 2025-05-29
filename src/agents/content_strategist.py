"""
Content Strategist agent for planning LinkedIn posts.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentStrategist(BaseAgent):
    """Agent that plans content strategy for LinkedIn posts."""
    
    def __init__(self):
        super().__init__(
            role="LinkedIn Content Strategy Expert",
            goal="Plan engaging LinkedIn posts that educate about AI safety while building COAI Research's thought leadership",
            backstory="""You are a content strategist with 8 years of experience in tech 
            and scientific communication. You specialize in making complex technical topics 
            accessible and engaging for professional audiences. You understand LinkedIn's 
            algorithm, best practices for engagement, and how to build authentic thought 
            leadership. You're skilled at identifying the right angle, timing, and 
            presentation style for maximum impact.""",
            verbose=True
        )
        
        # Content angles and strategies
        self.content_angles = [
            "educational",
            "thought-provoking",
            "news-commentary",
            "personal-insight",
            "controversial-take",
            "practical-application",
            "future-implications",
            "behind-the-research"
        ]
        
        self.visual_strategies = [
            "key-quote-graphic",
            "simple-diagram",
            "paper-screenshot",
            "thread-preview",
            "emoji-emphasis",
            "numbered-list",
            "comparison-table"
        ]
    
    def get_temperature(self) -> float:
        """Moderate temperature for creative strategy."""
        return 0.7
    
    def get_max_tokens(self) -> int:
        """Moderate tokens for strategy planning."""
        return 800
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan content strategy based on research insights.
        
        Args:
            context: Should contain 'research_analysis' from ResearchAnalyst
            
        Returns:
            Content strategy blueprint
        """
        research = context.get('research_analysis', {})
        target_audience = context.get('target_audience', 'AI researchers and tech leaders')
        post_goals = context.get('post_goals', ['educate', 'engage', 'build_authority'])
        
        # Select top content based on ratings
        top_content = self._select_top_content(research)
        
        # Plan content strategy
        strategy = {
            "timestamp": datetime.utcnow().isoformat(),
            "selected_content": top_content,
            "content_plans": []
        }
        
        # Create plans for each piece of content
        for content in top_content:
            plan = self._create_content_plan(content, target_audience, post_goals)
            strategy["content_plans"].append(plan)
        
        # Add posting schedule recommendation
        strategy["posting_schedule"] = self._recommend_posting_schedule(
            len(strategy["content_plans"])
        )
        
        return strategy
    
    def _select_top_content(self, research: Dict[str, Any]) -> List[Dict]:
        """Select the best content for posts."""
        candidates = []
        
        # Get highly rated papers
        if "content_ratings" in research:
            for rating in research["content_ratings"][:3]:
                if rating["rating"] >= 7:
                    candidates.append({
                        "type": "paper",
                        "id": rating["paper_id"],
                        "title": rating["title"],
                        "rating": rating["rating"],
                        "source": "research_paper"
                    })
        
        # Get breakthrough findings
        if "breakthrough_findings" in research:
            for finding in research["breakthrough_findings"][:2]:
                candidates.append({
                    "type": "breakthrough",
                    "id": finding["paper_id"],
                    "title": finding["title"],
                    "finding": finding["finding"],
                    "source": "breakthrough_research"
                })
        
        # Get viral discussions
        if "key_insights" in research:
            for insight in research["key_insights"]:
                if insight.get("type") == "viral_discussions":
                    candidates.append({
                        "type": "discussion",
                        "analysis": insight["analysis"],
                        "post_count": insight["post_count"],
                        "source": "viral_discussion"
                    })
        
        return candidates[:3]  # Top 3 pieces of content
    
    def _create_content_plan(
        self, 
        content: Dict[str, Any], 
        target_audience: str,
        post_goals: List[str]
    ) -> Dict[str, Any]:
        """Create detailed content plan for a piece of content."""
        # Choose content angle
        angle = self._choose_content_angle(content, post_goals)
        
        # Choose visual strategy
        visual = random.choice(self.visual_strategies)
        
        # Plan mentions and hashtags
        mentions = self._plan_mentions(content)
        hashtags = self._plan_hashtags(content, angle)
        
        # Create the plan
        prompt = f"""Create a LinkedIn content strategy for this content:

Content Type: {content['type']}
Source: {content['source']}
Title/Topic: {content.get('title', 'AI Safety Discussion')}
Target Audience: {target_audience}
Goals: {', '.join(post_goals)}
Chosen Angle: {angle}
Visual Strategy: {visual}

Please provide:
1. Hook/Opening (2-3 options)
2. Main points to cover (3-5 bullet points)
3. Call-to-action (2 options)
4. Tone and style guidelines
5. Optimal post length (words)
6. Key message to emphasize

Make it authentic and engaging, not robotic."""

        try:
            response = self.llm_config.complete(
                messages=[
                    {"role": "system", "content": self.backstory},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.get_temperature(),
                max_tokens=self.get_max_tokens()
            )
            
            strategy_details = response.choices[0].message.content
            
            return {
                "content_id": content.get('id', 'discussion'),
                "content_type": content['type'],
                "angle": angle,
                "visual_strategy": visual,
                "mentions": mentions,
                "hashtags": hashtags,
                "strategy_details": strategy_details,
                "estimated_engagement": self._estimate_engagement(content, angle)
            }
            
        except Exception as e:
            logger.error(f"Error creating content plan: {e}")
            return {
                "content_id": content.get('id', 'unknown'),
                "error": str(e)
            }
    
    def _choose_content_angle(self, content: Dict[str, Any], goals: List[str]) -> str:
        """Choose the best content angle based on content and goals."""
        if content['type'] == 'breakthrough':
            return random.choice(["news-commentary", "future-implications", "thought-provoking"])
        elif content['type'] == 'discussion':
            return random.choice(["controversial-take", "thought-provoking", "personal-insight"])
        elif 'educate' in goals:
            return random.choice(["educational", "practical-application", "behind-the-research"])
        else:
            return random.choice(self.content_angles)
    
    def _plan_mentions(self, content: Dict[str, Any]) -> List[str]:
        """Plan strategic mentions for the post."""
        mentions = []
        
        # Add paper authors if available
        if content.get('type') == 'paper' and 'authors' in content:
            # Would need LinkedIn handles - placeholder
            mentions.extend(["@paper_author1", "@paper_author2"])
        
        # Add thought leaders based on topic
        # This would be enhanced with actual LinkedIn network data
        if "safety" in str(content).lower():
            mentions.append("@ai_safety_leader")
        
        return mentions[:3]  # Max 3 mentions
    
    def _plan_hashtags(self, content: Dict[str, Any], angle: str) -> List[str]:
        """Plan relevant hashtags."""
        hashtags = ["#AISafety", "#AIAlignment"]
        
        # Add angle-specific hashtags
        angle_hashtags = {
            "educational": ["#AIEducation", "#TechExplained"],
            "thought-provoking": ["#FutureOfAI", "#AIEthics"],
            "news-commentary": ["#AINews", "#TechNews"],
            "controversial-take": ["#AIDebate", "#TechDebate"],
            "practical-application": ["#AIImplementation", "#TechInnovation"]
        }
        
        if angle in angle_hashtags:
            hashtags.extend(angle_hashtags[angle])
        
        # Add content-specific hashtags
        if content.get('type') == 'breakthrough':
            hashtags.append("#AIBreakthrough")
        elif content.get('type') == 'discussion':
            hashtags.append("#AIDiscussion")
        
        return list(set(hashtags))[:5]  # Max 5 hashtags
    
    def _estimate_engagement(self, content: Dict[str, Any], angle: str) -> str:
        """Estimate potential engagement level."""
        score = 5  # Base score
        
        # Boost for certain content types
        if content.get('type') == 'breakthrough':
            score += 3
        elif content.get('type') == 'discussion':
            score += 2
        
        # Boost for certain angles
        if angle in ['controversial-take', 'thought-provoking']:
            score += 2
        elif angle in ['educational', 'practical-application']:
            score += 1
        
        # Rating boost
        if content.get('rating', 0) >= 8:
            score += 2
        
        if score >= 9:
            return "very high"
        elif score >= 7:
            return "high"
        elif score >= 5:
            return "medium"
        else:
            return "low"
    
    def _recommend_posting_schedule(self, num_posts: int) -> Dict[str, Any]:
        """Recommend posting schedule."""
        return {
            "posts_per_week": min(num_posts, 3),
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_times": ["8:00 AM", "12:00 PM", "5:00 PM"],
            "spacing": "at least 48 hours between posts",
            "notes": "Avoid Mondays and Fridays for maximum engagement"
        }