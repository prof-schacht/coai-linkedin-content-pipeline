"""
Content pipeline orchestrator that brings together all components
to generate LinkedIn posts.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from src.models.base import get_db
from src.models.generated_post import GeneratedPost, ContentTemplate
from src.collectors.arxiv_monitor import ArxivMonitor
from src.collectors.x_scanner import XScanner
from src.generators.content_scorer import ContentScorer, ContentOpportunity
from src.agents.crew_manager import CrewManager
from src.analyzers.network_mapper import NetworkMapper
from config.litellm_config import LiteLLMConfig

logger = logging.getLogger(__name__)


class ContentPipeline:
    """Main content generation pipeline orchestrator."""
    
    def __init__(self):
        self.arxiv_monitor = ArxivMonitor()
        self.x_scanner = XScanner()
        self.content_scorer = ContentScorer()
        self.crew_manager = CrewManager()
        self.network_mapper = NetworkMapper()
        self.llm_config = LiteLLMConfig()
        
        # Pipeline configuration
        self.daily_post_target = 2
        self.min_quality_score = 7.0
        self.max_posts_per_day = 3
        
        # Content guidelines
        self.max_content_length = 2900  # LinkedIn limit is 3000
        self.required_hashtags = ['#AISafety', '#MechanisticInterpretability']
        self.coai_website = 'https://coairesearch.org'
        
    async def daily_run(self) -> Dict[str, any]:
        """
        Execute the daily content generation pipeline.
        
        Returns:
            Dictionary with pipeline results and statistics
        """
        logger.info("Starting daily content pipeline run")
        start_time = datetime.utcnow()
        
        stats = {
            'start_time': start_time,
            'papers_collected': 0,
            'x_posts_collected': 0,
            'opportunities_scored': 0,
            'posts_generated': 0,
            'posts_approved': 0,
            'errors': []
        }
        
        try:
            # Step 1: Collect fresh content
            await self._collect_fresh_content(stats)
            
            # Step 2: Score and rank opportunities
            opportunities = self._score_content_opportunities(stats)
            
            # Step 3: Generate posts for top opportunities
            generated_posts = await self._generate_posts(opportunities, stats)
            
            # Step 4: Review and approve posts
            approved_posts = self._review_posts(generated_posts, stats)
            
            # Step 5: Schedule approved posts
            self._schedule_posts(approved_posts, stats)
            
            stats['end_time'] = datetime.utcnow()
            stats['duration'] = (stats['end_time'] - start_time).total_seconds()
            stats['success'] = True
            
            logger.info(f"Pipeline completed successfully: {stats}")
            
        except Exception as e:
            stats['errors'].append(str(e))
            stats['success'] = False
            logger.error(f"Pipeline failed: {e}")
            raise
        
        return stats
    
    async def _collect_fresh_content(self, stats: Dict) -> None:
        """Collect fresh content from arXiv and X.com."""
        logger.info("Collecting fresh content...")
        
        try:
            # Collect arXiv papers (last 2 days to catch any missed ones)
            arxiv_stats = self.arxiv_monitor.fetch_papers_since_date(
                days_ago=2,
                max_papers=50
            )
            stats['papers_collected'] = arxiv_stats.get('papers_fetched', 0)
            
            # Collect X.com posts (last 1 day)
            x_stats = await self.x_scanner.monitor_daily()
            stats['x_posts_collected'] = x_stats.get('posts_collected', 0)
            
        except Exception as e:
            error_msg = f"Content collection failed: {e}"
            stats['errors'].append(error_msg)
            logger.error(error_msg)
    
    def _score_content_opportunities(self, stats: Dict) -> List[ContentOpportunity]:
        """Score and rank content opportunities."""
        logger.info("Scoring content opportunities...")
        
        try:
            opportunities = self.content_scorer.get_top_opportunities(
                count=self.daily_post_target * 2,  # Get more than needed
                days=7
            )
            
            stats['opportunities_scored'] = len(opportunities)
            logger.info(f"Found {len(opportunities)} content opportunities")
            
            return opportunities
            
        except Exception as e:
            error_msg = f"Content scoring failed: {e}"
            stats['errors'].append(error_msg)
            logger.error(error_msg)
            return []
    
    async def _generate_posts(
        self, 
        opportunities: List[ContentOpportunity],
        stats: Dict
    ) -> List[GeneratedPost]:
        """Generate posts for the best opportunities."""
        logger.info(f"Generating posts for {len(opportunities)} opportunities...")
        
        generated_posts = []
        
        for i, opportunity in enumerate(opportunities[:self.daily_post_target]):
            try:
                logger.info(f"Generating post {i+1} for: {opportunity.title}")
                
                # Generate post using CrewAI agents
                post_content = await self._run_agent_workflow(opportunity)
                
                # Create database record
                generated_post = self._create_post_record(opportunity, post_content)
                
                # Calculate quality score
                self._score_post_quality(generated_post)
                
                if generated_post.quality_score >= self.min_quality_score:
                    generated_posts.append(generated_post)
                    stats['posts_generated'] += 1
                else:
                    logger.warning(f"Post quality too low: {generated_post.quality_score}")
                
            except Exception as e:
                error_msg = f"Post generation failed for opportunity {i+1}: {e}"
                stats['errors'].append(error_msg)
                logger.error(error_msg)
        
        return generated_posts
    
    async def _run_agent_workflow(self, opportunity: ContentOpportunity) -> Dict:
        """Run the CrewAI agent workflow to generate content."""
        
        # Prepare input data for agents
        input_data = {
            'content_type': opportunity.content_type,
            'source_data': opportunity.source_data,
            'recommended_angle': opportunity.recommended_angle,
            'target_audience': 'AI safety researchers and professionals',
            'platform': 'LinkedIn',
            'max_length': self.max_content_length
        }
        
        # Run the crew workflow (simplified for now)
        # In a full implementation, this would use the crew manager
        result = {
            'content': f"Generated content about {input_data.get('recommended_angle', 'AI research')}",
            'hashtags': ['#AISafety', '#MechanisticInterpretability'],
            'mentions': [],
            'visual_path': None
        }
        
        return result
    
    def _create_post_record(
        self, 
        opportunity: ContentOpportunity,
        agent_output: Dict
    ) -> GeneratedPost:
        """Create a GeneratedPost database record."""
        
        with get_db() as db:
            # Extract paper/x_post IDs based on content type
            paper_id = None
            x_post_ids = None
            
            if opportunity.content_type == 'paper':
                paper_id = opportunity.source_id
            elif opportunity.content_type in ['x_discussion', 'trend_analysis']:
                if opportunity.content_type == 'x_discussion':
                    x_post_ids = [opportunity.source_id]
                else:  # trend_analysis
                    paper_id = opportunity.source_id
                    # Could also include related X post IDs
            
            # Create the post
            post = GeneratedPost(
                paper_id=paper_id,
                x_post_ids=x_post_ids,
                content=agent_output.get('content', ''),
                mentions=agent_output.get('mentions', []),
                hashtags=agent_output.get('hashtags', self.required_hashtags),
                visual_path=agent_output.get('visual_path'),
                status='draft',
                engagement_prediction=opportunity.total_score / 10.0  # Convert to 0-1 scale
            )
            
            db.add(post)
            db.commit()
            db.refresh(post)
            
            logger.info(f"Created post record with ID: {post.id}")
            return post
    
    def _score_post_quality(self, post: GeneratedPost) -> None:
        """Score the quality of a generated post."""
        
        quality_score = 5.0  # Base score
        
        # Content length check
        content_length = len(post.content)
        if 200 <= content_length <= self.max_content_length:
            quality_score += 1.0
        elif content_length > self.max_content_length:
            quality_score -= 2.0
        
        # Hashtag check
        if post.hashtags and len(post.hashtags) >= 2:
            quality_score += 0.5
        
        # Mention check
        if post.mentions and len(post.mentions) >= 1:
            quality_score += 0.5
        
        # Content quality heuristics
        if post.content:
            content_lower = post.content.lower()
            
            # Check for engagement elements
            if any(char in post.content for char in ['?', '!']):
                quality_score += 0.5
            
            # Check for AI safety keywords
            safety_keywords = ['ai safety', 'alignment', 'interpretability', 'control']
            keyword_matches = sum(1 for kw in safety_keywords if kw in content_lower)
            quality_score += min(keyword_matches * 0.5, 1.5)
            
            # Check for authenticity (not too robotic)
            robotic_phrases = ['leverage', 'optimize', 'utilize', 'furthermore', 'moreover']
            robotic_count = sum(1 for phrase in robotic_phrases if phrase in content_lower)
            quality_score -= min(robotic_count * 0.3, 1.0)
        
        # Store quality score
        post.quality_score = min(quality_score, 10.0)
        
        with get_db() as db:
            db.merge(post)
            db.commit()
    
    def _review_posts(self, posts: List[GeneratedPost], stats: Dict) -> List[GeneratedPost]:
        """Review generated posts and approve/reject them."""
        logger.info(f"Reviewing {len(posts)} generated posts...")
        
        approved_posts = []
        
        for post in posts:
            # Automatic approval criteria
            should_approve = (
                post.quality_score >= self.min_quality_score and
                len(post.content) <= self.max_content_length and
                post.content and  # Not empty
                not self._contains_problematic_content(post.content)
            )
            
            if should_approve:
                post.status = 'approved'
                approved_posts.append(post)
                stats['posts_approved'] += 1
                logger.info(f"Auto-approved post {post.id} (quality: {post.quality_score})")
            else:
                post.status = 'needs_review'
                logger.warning(f"Post {post.id} needs manual review (quality: {post.quality_score})")
            
            # Update status in database
            with get_db() as db:
                db.merge(post)
                db.commit()
        
        return approved_posts
    
    def _contains_problematic_content(self, content: str) -> bool:
        """Check if content contains potentially problematic elements."""
        
        problematic_terms = [
            'click here', 'buy now', 'limited time',
            'guaranteed', 'revolutionary breakthrough',
            'shocking', 'you won\'t believe'
        ]
        
        content_lower = content.lower()
        
        for term in problematic_terms:
            if term in content_lower:
                return True
        
        # Check for excessive caps or punctuation
        if content.count('!') > 3 or content.count('?') > 3:
            return True
        
        return False
    
    def _schedule_posts(self, posts: List[GeneratedPost], stats: Dict) -> None:
        """Schedule approved posts for publishing."""
        logger.info(f"Scheduling {len(posts)} approved posts...")
        
        # Optimal posting times (Tuesday-Thursday, 8-10 AM PST)
        base_time = datetime.utcnow().replace(hour=16, minute=0, second=0)  # 8 AM PST
        
        for i, post in enumerate(posts):
            # Space posts out by 4-6 hours
            scheduled_time = base_time + timedelta(hours=i * 5)
            
            # Move to next optimal day if too many posts
            if i >= self.max_posts_per_day:
                scheduled_time += timedelta(days=1)
            
            post.scheduled_for = scheduled_time
            
            with get_db() as db:
                db.merge(post)
                db.commit()
            
            logger.info(f"Scheduled post {post.id} for {scheduled_time}")
    
    def get_pipeline_stats(self, days: int = 7) -> Dict:
        """Get pipeline performance statistics."""
        
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic stats
            total_posts = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= cutoff_date
            ).count()
            
            approved_posts = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= cutoff_date,
                GeneratedPost.status == 'approved'
            ).count()
            
            posted_posts = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= cutoff_date,
                GeneratedPost.posted_at.is_not(None)
            ).count()
            
            # Quality stats
            from sqlalchemy import func
            avg_quality = db.query(func.avg(GeneratedPost.quality_score)).filter(
                GeneratedPost.created_at >= cutoff_date,
                GeneratedPost.quality_score.is_not(None)
            ).scalar() or 0
            
            return {
                'period_days': days,
                'total_posts_generated': total_posts,
                'posts_approved': approved_posts,
                'posts_published': posted_posts,
                'approval_rate': approved_posts / max(total_posts, 1),
                'average_quality_score': round(avg_quality, 2),
                'posts_per_day': total_posts / days
            }
    
    async def generate_emergency_post(
        self, 
        topic: str,
        urgency: str = 'high'
    ) -> Optional[GeneratedPost]:
        """Generate an emergency post for breaking news or important topics."""
        logger.info(f"Generating emergency post for topic: {topic}")
        
        # Create a synthetic opportunity
        opportunity = ContentOpportunity(
            content_type='emergency',
            source_id=0,
            title=f"Emergency: {topic}",
            description=f"Urgent content about {topic}",
            novelty_score=10.0,
            relevance_score=10.0,
            timeliness_score=10.0,
            engagement_potential=9.0,
            visual_potential=5.0,
            total_score=9.0,
            source_data={'topic': topic, 'urgency': urgency},
            recommended_angle=f"COAI perspective on {topic}",
            suggested_mentions=[]
        )
        
        # Generate post
        agent_output = await self._run_agent_workflow(opportunity)
        post = self._create_post_record(opportunity, agent_output)
        self._score_post_quality(post)
        
        # Auto-approve high-quality emergency posts
        if post.quality_score >= 7.0:
            post.status = 'approved'
            # Schedule for immediate posting (next optimal slot)
            post.scheduled_for = datetime.utcnow() + timedelta(hours=1)
            
            with get_db() as db:
                db.merge(post)
                db.commit()
            
            logger.info(f"Emergency post generated and approved: {post.id}")
            return post
        
        return None