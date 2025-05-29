"""
CrewAI manager for orchestrating multi-agent content generation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Crew, Task
from crewai.process import Process

from .research_analyst import ResearchAnalyst
from .content_strategist import ContentStrategist
from .linkedin_writer import LinkedInWriter
from .interview_scout import InterviewScout
from src.models.paper import Paper
from src.models.x_post import XPost
from src.models.base import get_db

logger = logging.getLogger(__name__)


class CrewManager:
    """Manages the CrewAI multi-agent system for content generation."""
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the crew manager with all agents.
        
        Args:
            verbose: Whether to log detailed agent interactions
        """
        self.verbose = verbose
        
        # Initialize agents
        self.research_analyst = ResearchAnalyst()
        self.content_strategist = ContentStrategist()
        self.linkedin_writer = LinkedInWriter()
        self.interview_scout = InterviewScout()
        
        logger.info("Initialized CrewManager with all agents")
    
    def generate_content(
        self,
        papers: Optional[List[Paper]] = None,
        posts: Optional[List[XPost]] = None,
        network_data: Optional[Dict[str, Any]] = None,
        num_posts: int = 2
    ) -> Dict[str, Any]:
        """
        Generate LinkedIn content using the multi-agent system.
        
        Args:
            papers: List of Paper objects to analyze
            posts: List of XPost objects to analyze
            network_data: LinkedIn network information
            num_posts: Number of posts to generate
            
        Returns:
            Generated content and analysis results
        """
        start_time = datetime.utcnow()
        
        try:
            # If no data provided, fetch recent data
            if not papers and not posts:
                papers, posts = self._fetch_recent_data()
            
            if not papers and not posts:
                raise ValueError("No data available for content generation")
            
            # Create context for agents
            context = {
                "papers": papers,
                "posts": posts,
                "network_data": network_data or {},
                "num_posts": num_posts,
                "timestamp": start_time.isoformat()
            }
            
            # Execute agent pipeline
            results = {}
            
            # Step 1: Research Analysis
            logger.info("Step 1: Research Analysis")
            research_results = self.research_analyst.execute(context)
            results["research_analysis"] = research_results["output"]
            
            # Step 2: Content Strategy
            logger.info("Step 2: Content Strategy")
            strategy_context = {
                **context,
                "research_analysis": research_results["output"]
            }
            strategy_results = self.content_strategist.execute(strategy_context)
            results["content_strategy"] = strategy_results["output"]
            
            # Step 3: Write Posts
            logger.info("Step 3: Writing Posts")
            posts_written = []
            content_plans = strategy_results["output"].get("content_plans", [])[:num_posts]
            
            for plan in content_plans:
                writer_context = {
                    "content_plan": plan,
                    "research_data": research_results["output"]
                }
                writer_results = self.linkedin_writer.execute(writer_context)
                posts_written.append(writer_results["output"])
            
            results["linkedin_posts"] = posts_written
            
            # Step 4: Interview Candidates (parallel task)
            logger.info("Step 4: Identifying Interview Candidates")
            scout_results = self.interview_scout.execute(context)
            results["interview_candidates"] = scout_results["output"]
            
            # Generate summary
            results["summary"] = self._generate_summary(results)
            results["execution_time"] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Content generation completed in {results['execution_time']:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"Error in content generation: {e}")
            return {
                "error": str(e),
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
    
    def create_crew_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """
        Create CrewAI tasks for the agents.
        
        Args:
            context: Context data for tasks
            
        Returns:
            List of CrewAI Task objects
        """
        tasks = []
        
        # Research Analysis Task
        analyze_task = Task(
            description=f"""Analyze {len(context.get('papers', []))} papers and 
            {len(context.get('posts', []))} social media posts about AI safety.
            Extract key insights, identify breakthroughs, and rate content potential.""",
            agent=self.research_analyst.agent,
            expected_output="Structured analysis with insights and content ratings"
        )
        tasks.append(analyze_task)
        
        # Content Strategy Task
        strategy_task = Task(
            description="""Based on the research analysis, create content strategies 
            for LinkedIn posts. Choose the best angles, plan visuals, and optimize 
            for engagement.""",
            agent=self.content_strategist.agent,
            expected_output="Content plans with angles, visuals, and hashtags",
            context=[analyze_task]
        )
        tasks.append(strategy_task)
        
        # Writing Task
        writing_task = Task(
            description="""Write authentic LinkedIn posts based on the content strategies.
            Make them engaging, human-sounding, and aligned with COAI Research's voice.""",
            agent=self.linkedin_writer.agent,
            expected_output="LinkedIn posts ready for publication",
            context=[strategy_task]
        )
        tasks.append(writing_task)
        
        # Interview Scout Task (can run in parallel)
        scout_task = Task(
            description="""Identify and evaluate potential podcast interview candidates
            from the papers and discussions. Rank them and provide outreach strategies.""",
            agent=self.interview_scout.agent,
            expected_output="Ranked list of interview candidates with evaluations"
        )
        tasks.append(scout_task)
        
        return tasks
    
    def run_crew(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the full CrewAI crew with all agents.
        
        Args:
            context: Context data for the crew
            
        Returns:
            Crew execution results
        """
        try:
            # Create tasks
            tasks = self.create_crew_tasks(context)
            
            # Create crew
            crew = Crew(
                agents=[
                    self.research_analyst.agent,
                    self.content_strategist.agent,
                    self.linkedin_writer.agent,
                    self.interview_scout.agent
                ],
                tasks=tasks,
                process=Process.sequential,  # Can also use Process.hierarchical
                verbose=self.verbose
            )
            
            # Execute crew
            result = crew.kickoff()
            
            return {
                "status": "success",
                "result": result,
                "tasks_completed": len(tasks)
            }
            
        except Exception as e:
            logger.error(f"Crew execution failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _fetch_recent_data(self) -> tuple:
        """Fetch recent papers and posts from database."""
        with get_db() as db:
            # Get recent high-quality papers
            papers = db.query(Paper).filter(
                Paper.relevance_score >= 0.6,
                Paper.processed == False
            ).order_by(
                Paper.submission_date.desc()
            ).limit(10).all()
            
            # Get recent viral posts
            posts = db.query(XPost).filter(
                XPost.relevance_score >= 0.6,
                XPost.processed == False
            ).order_by(
                XPost.posted_at.desc()
            ).limit(20).all()
            
            return papers, posts
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution summary."""
        summary = {
            "papers_analyzed": 0,
            "posts_analyzed": 0,
            "content_generated": 0,
            "candidates_identified": 0,
            "top_insights": [],
            "recommended_posting_schedule": {}
        }
        
        # Extract summary data
        if "research_analysis" in results:
            analysis = results["research_analysis"]
            summary["papers_analyzed"] = analysis.get("papers_analyzed", 0)
            summary["posts_analyzed"] = analysis.get("posts_analyzed", 0)
            
            # Get top insights
            insights = analysis.get("key_insights", [])
            summary["top_insights"] = [
                insight.get("analysis", "")[:200] 
                for insight in insights[:3]
            ]
        
        if "linkedin_posts" in results:
            summary["content_generated"] = len(results["linkedin_posts"])
        
        if "interview_candidates" in results:
            candidates = results["interview_candidates"]
            summary["candidates_identified"] = candidates.get("total_candidates", 0)
        
        if "content_strategy" in results:
            strategy = results["content_strategy"]
            summary["recommended_posting_schedule"] = strategy.get("posting_schedule", {})
        
        return summary