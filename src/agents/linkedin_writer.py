"""
LinkedIn Writer agent for creating authentic posts.
"""

import logging
import random
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LinkedInWriter(BaseAgent):
    """Agent that writes authentic LinkedIn posts."""
    
    def __init__(self):
        super().__init__(
            role="LinkedIn Content Writer & AI Researcher",
            goal="Write authentic, engaging LinkedIn posts that sound human while educating about AI safety",
            backstory="""You are a tech writer and AI researcher who has been active on 
            LinkedIn for 5 years. You've built a following by sharing genuine insights 
            about AI development in an accessible way. Your writing style is conversational 
            yet professional, often starting with personal observations or questions. 
            You use emojis sparingly but effectively, and you're not afraid to express 
            uncertainty or ask for others' opinions. You avoid corporate jargon and 
            AI-generated-sounding phrases.""",
            verbose=True
        )
        
        # Writing patterns for authenticity
        self.opening_patterns = [
            "Been diving into {topic} and found something fascinating...",
            "Quick thought on {topic} after reading {source}:",
            "This might be controversial, but {insight}...",
            "I've been thinking about {topic} lately, and here's what struck me:",
            "Just came across {finding} and it got me thinking...",
            "Unpopular opinion: {insight}",
            "Here's something that surprised me about {topic}:",
            "{emoji} Hot take on {topic}:",
            "Can we talk about {topic} for a minute?",
            "I used to think {old_view}, but {new_view}..."
        ]
        
        self.transition_phrases = [
            "Here's what stood out:",
            "The key insight?",
            "What this means for AI safety:",
            "But here's the interesting part:",
            "The implications are huge:",
            "What really got me was:",
            "Think about it this way:",
            "Here's my take:",
            "The surprising bit:"
        ]
        
        self.closing_patterns = [
            "What's your take on this?",
            "Am I overthinking this?",
            "Would love to hear your thoughts 👇",
            "Curious what others think about this approach",
            "What am I missing here?",
            "Anyone else seeing this trend?",
            "Thoughts? Agree/disagree?",
            "What's your experience been?",
            "Let me know if this resonates"
        ]
        
        self.emoji_patterns = {
            "thinking": ["🤔", "💭", "🧠"],
            "insight": ["💡", "✨", "🔍"],
            "warning": ["⚠️", "🚨", "⚡"],
            "positive": ["🎯", "✅", "💪"],
            "surprising": ["😮", "👀", "🤯"],
            "technical": ["🔬", "⚙️", "🛠️"],
            "discussion": ["💬", "🗣️", "👇"]
        }
    
    def get_temperature(self) -> float:
        """Higher temperature for creative writing."""
        return 0.8
    
    def get_max_tokens(self) -> int:
        """Sufficient tokens for a full post."""
        return 600
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write LinkedIn post based on content strategy.
        
        Args:
            context: Should contain 'content_plan' from ContentStrategist
            
        Returns:
            Draft LinkedIn posts
        """
        content_plan = context.get('content_plan', {})
        research_data = context.get('research_data', {})
        
        if not content_plan:
            raise ValueError("No content plan provided")
        
        # Generate multiple draft variations
        drafts = []
        for i in range(2):  # Create 2 variations
            draft = self._write_post(content_plan, research_data, variation=i)
            drafts.append(draft)
        
        # Select best draft
        best_draft = self._select_best_draft(drafts)
        
        return {
            "primary_draft": best_draft,
            "alternative_drafts": drafts,
            "metadata": {
                "word_count": len(best_draft["content"].split()),
                "hashtags": best_draft["hashtags"],
                "mentions": best_draft["mentions"],
                "estimated_read_time": f"{len(best_draft['content'].split()) // 200} min"
            }
        }
    
    def _write_post(
        self, 
        content_plan: Dict[str, Any], 
        research_data: Dict[str, Any],
        variation: int = 0
    ) -> Dict[str, Any]:
        """Write a single post draft."""
        angle = content_plan.get('angle', 'educational')
        visual_strategy = content_plan.get('visual_strategy', 'emoji-emphasis')
        strategy_details = content_plan.get('strategy_details', '')
        
        # Build context for writing
        writing_context = f"""Write a LinkedIn post based on this strategy:

Content Type: {content_plan.get('content_type', 'research')}
Angle: {angle}
Visual Strategy: {visual_strategy}
Strategy Details:
{strategy_details}

Additional Context:
{self._format_research_context(research_data)}

Writing Guidelines:
- Start with one of these patterns: {random.choice(self.opening_patterns)}
- Use natural, conversational tone
- Include 1-2 relevant emojis max
- Vary sentence length
- Add a personal observation or question
- End with engagement prompt
- Target length: 150-300 words
- Make it feel authentic, not AI-generated

Variation {variation + 1}: {'More casual/personal' if variation == 0 else 'More professional/analytical'}"""

        try:
            response = self.llm_config.complete(
                messages=[
                    {"role": "system", "content": self.backstory},
                    {"role": "user", "content": writing_context}
                ],
                temperature=self.get_temperature() + (0.1 * variation),
                max_tokens=self.get_max_tokens()
            )
            
            post_content = response.choices[0].message.content
            
            # Add humanizing touches
            post_content = self._add_humanizing_touches(post_content, angle)
            
            return {
                "content": post_content,
                "angle": angle,
                "variation": variation,
                "hashtags": content_plan.get('hashtags', []),
                "mentions": content_plan.get('mentions', []),
                "visual_strategy": visual_strategy
            }
            
        except Exception as e:
            logger.error(f"Error writing post: {e}")
            return {
                "content": "Error generating post",
                "error": str(e)
            }
    
    def _format_research_context(self, research_data: Dict[str, Any]) -> str:
        """Format research data for the writing prompt."""
        context_parts = []
        
        if "key_insights" in research_data:
            insights = research_data["key_insights"][:2]
            context_parts.append("Key Insights:\n" + "\n".join(
                f"- {insight.get('analysis', '')[:200]}..." for insight in insights
            ))
        
        if "breakthrough_findings" in research_data:
            findings = research_data["breakthrough_findings"][:1]
            if findings:
                context_parts.append(f"Breakthrough: {findings[0].get('finding', '')[:200]}...")
        
        return "\n\n".join(context_parts)
    
    def _add_humanizing_touches(self, content: str, angle: str) -> str:
        """Add authentic human touches to the post."""
        # Add natural variations
        replacements = [
            ("I am", "I'm"),
            ("It is", "It's"),
            ("We are", "We're"),
            ("Do not", "Don't"),
            ("Cannot", "Can't"),
            ("Will not", "Won't")
        ]
        
        for old, new in replacements:
            if random.random() > 0.5:  # 50% chance
                content = content.replace(old, new)
                content = content.replace(old.lower(), new.lower())
        
        # Add occasional informal touches
        if angle in ["personal-insight", "controversial-take"]:
            informal_additions = [
                ("interesting", "really interesting"),
                ("important", "super important"),
                ("confused", "a bit confused"),
                ("surprised", "genuinely surprised")
            ]
            
            for formal, informal in informal_additions:
                if formal in content.lower() and random.random() > 0.6:
                    content = content.replace(formal, informal, 1)
        
        # Add thinking pauses
        if random.random() > 0.7:
            pause_phrases = ["...", " - ", "—"]
            words = content.split()
            if len(words) > 20:
                insert_pos = random.randint(10, len(words) - 10)
                words.insert(insert_pos, random.choice(pause_phrases))
                content = " ".join(words)
        
        return content
    
    def _select_best_draft(self, drafts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best draft based on quality criteria."""
        scored_drafts = []
        
        for draft in drafts:
            if "error" in draft:
                continue
                
            score = 0
            content = draft["content"]
            
            # Length score (150-300 words ideal)
            word_count = len(content.split())
            if 150 <= word_count <= 300:
                score += 3
            elif 100 <= word_count <= 400:
                score += 1
            
            # Engagement elements
            if any(pattern in content for pattern in ["?", "What's your", "Thoughts", "Curious"]):
                score += 2
            
            # Personal elements
            if any(word in content.lower() for word in ["i've", "i'm", "my", "me"]):
                score += 1
            
            # Emoji usage (sparse is good)
            emoji_count = sum(1 for char in content if ord(char) > 127000)
            if 1 <= emoji_count <= 3:
                score += 1
            
            scored_drafts.append((score, draft))
        
        # Return highest scoring draft
        scored_drafts.sort(key=lambda x: x[0], reverse=True)
        return scored_drafts[0][1] if scored_drafts else drafts[0]