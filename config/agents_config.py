"""
Configuration for CrewAI agents.
"""

import os
from typing import Dict, Any

# Agent configuration
AGENT_CONFIG = {
    "research_analyst": {
        "temperature": 0.3,
        "max_tokens": 1000,
        "timeout": 30,
        "retry_attempts": 2
    },
    "content_strategist": {
        "temperature": 0.7,
        "max_tokens": 800,
        "timeout": 25,
        "retry_attempts": 2
    },
    "linkedin_writer": {
        "temperature": 0.8,
        "max_tokens": 600,
        "timeout": 20,
        "retry_attempts": 3,
        "variations_per_post": 2
    },
    "interview_scout": {
        "temperature": 0.4,
        "max_tokens": 700,
        "timeout": 25,
        "retry_attempts": 2,
        "max_candidates": 20
    }
}

# CrewAI settings
CREW_CONFIG = {
    "max_iterations": 5,
    "verbose": os.getenv("CREW_VERBOSE", "True").lower() == "true",
    "memory": True,
    "cache": True,
    "max_parallel_tasks": 2
}

# Content generation settings
CONTENT_CONFIG = {
    "posts_per_run": int(os.getenv("POSTS_PER_DAY", "2")),
    "min_content_score": 7.0,
    "max_post_length": 3000,  # LinkedIn limit
    "min_post_length": 100,
    "ideal_post_length": 150,  # 150-300 words
    "max_hashtags": 5,
    "max_mentions": 3,
    "emoji_limit": 3
}

# Writing style preferences
WRITING_STYLE = {
    "formality": "conversational",  # formal, conversational, casual
    "perspective": "first_person",  # first_person, third_person
    "tone": ["informative", "thought-provoking", "engaging"],
    "avoid_phrases": [
        "In conclusion",
        "It's important to note",
        "As we all know",
        "At the end of the day",
        "Let that sink in",
        "Game-changer",
        "Leverage",
        "Synergy"
    ],
    "preferred_openers": [
        "question",
        "personal_observation",
        "surprising_fact",
        "controversial_statement"
    ]
}

# Interview candidate criteria
INTERVIEW_CRITERIA = {
    "min_relevance_score": 0.7,
    "min_papers": 2,
    "min_engagement": 1000,
    "preferred_topics": [
        "AI alignment",
        "interpretability",
        "AI safety",
        "AI control",
        "technical governance"
    ],
    "evaluation_weights": {
        "expertise": 0.25,
        "communication": 0.25,
        "relevance": 0.20,
        "reach": 0.15,
        "uniqueness": 0.15
    }
}

# Quality thresholds
QUALITY_THRESHOLDS = {
    "min_insight_quality": float(os.getenv("MIN_QUALITY_SCORE", "7.0")),
    "min_relevance_score": float(os.getenv("MIN_RELEVANCE_SCORE", "0.6")),
    "min_engagement_prediction": "medium",
    "require_fact_check": True,
    "require_source_citation": True
}

# Posting schedule preferences
POSTING_SCHEDULE = {
    "preferred_days": ["Tuesday", "Wednesday", "Thursday"],
    "preferred_times": ["08:00", "12:00", "17:00"],  # UTC
    "min_hours_between_posts": 48,
    "avoid_weekends": True,
    "avoid_holidays": True
}

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    return AGENT_CONFIG.get(agent_name, {})