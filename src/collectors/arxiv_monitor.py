"""
arXiv paper monitoring and collection system.
Fetches and analyzes AI-related papers from cs.AI and cs.CL categories.
"""

import os
import re
import time
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import arxiv
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.paper import Paper
from config.litellm_config import get_litellm_config

logger = logging.getLogger(__name__)


class ArxivMonitor:
    """Monitor and collect papers from arXiv."""
    
    def __init__(self):
        # Load configuration
        self.categories = os.getenv("ARXIV_CATEGORIES", "cs.AI,cs.CL,cs.LG,stat.ML").split(",")
        self.max_results = int(os.getenv("ARXIV_MAX_RESULTS_PER_DAY", "50"))
        self.lookback_days = int(os.getenv("ARXIV_LOOKBACK_DAYS", "7"))
        
        # AI safety topics for filtering
        self.topics = os.getenv(
            "TOPICS",
            "ai safety,ai alignment,ai control,technical governance,mechanistic interpretability,ai risk,interpretability"
        ).split(",")
        self.topics = [topic.strip().lower() for topic in self.topics]
        
        # Known AI safety researchers (can be expanded)
        self.known_researchers = [
            "stuart russell", "yoshua bengio", "max tegmark", "eliezer yudkowsky",
            "nick bostrom", "paul christiano", "dario amodei", "jan leike",
            "chris olah", "anthropic", "deepmind safety", "openai safety"
        ]
        
        self.llm_config = get_litellm_config()
        
    def search_papers(self, start_date: Optional[date] = None) -> List[arxiv.Result]:
        """
        Search for papers in specified categories.
        
        Args:
            start_date: Start date for paper search (defaults to lookback_days ago)
            
        Returns:
            List of arxiv.Result objects
        """
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=self.lookback_days)).date()
        
        # Build query for categories
        category_query = " OR ".join([f"cat:{cat}" for cat in self.categories])
        
        logger.info(f"Searching arXiv with query: {category_query}")
        logger.info(f"Date range: {start_date} to today")
        
        search = arxiv.Search(
            query=category_query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        results = []
        for result in search.results():
            # Filter by date
            submission_date = result.published.date()
            if submission_date >= start_date:
                results.append(result)
                
        logger.info(f"Found {len(results)} papers from the last {self.lookback_days} days")
        return results
    
    def calculate_relevance_score(self, paper: arxiv.Result) -> Tuple[float, List[str]]:
        """
        Calculate relevance score for a paper based on AI safety topics.
        
        Args:
            paper: arxiv.Result object
            
        Returns:
            Tuple of (score, matched_keywords)
        """
        score = 0.0
        matched_keywords = []
        
        # Prepare text for matching
        title_lower = paper.title.lower()
        abstract_lower = paper.summary.lower()
        authors_text = " ".join([author.name.lower() for author in paper.authors])
        
        # Check title matches (higher weight)
        for topic in self.topics:
            if topic in title_lower:
                score += 0.3
                matched_keywords.append(f"title:{topic}")
        
        # Check abstract matches
        for topic in self.topics:
            if topic in abstract_lower:
                score += 0.1
                if f"title:{topic}" not in matched_keywords:
                    matched_keywords.append(f"abstract:{topic}")
        
        # Check for known researchers
        for researcher in self.known_researchers:
            if researcher in authors_text:
                score += 0.2
                matched_keywords.append(f"author:{researcher}")
        
        # Check for specific AI safety related terms in abstract
        safety_terms = [
            "alignment", "interpretability", "mechanistic", "control problem",
            "value alignment", "corrigibility", "mesa-optimization", "inner alignment",
            "outer alignment", "reward hacking", "specification gaming", "robustness"
        ]
        
        for term in safety_terms:
            if term in abstract_lower:
                score += 0.05
                matched_keywords.append(f"term:{term}")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return score, matched_keywords
    
    def summarize_paper(self, paper: arxiv.Result) -> Optional[str]:
        """
        Generate a concise summary of the paper using LLM.
        
        Args:
            paper: arxiv.Result object
            
        Returns:
            Summary string or None if failed
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an AI safety researcher. Summarize academic papers concisely, focusing on their relevance to AI safety, control, and interpretability."
                },
                {
                    "role": "user",
                    "content": f"""Summarize this paper in 2-3 sentences, focusing on its relevance to AI safety:

Title: {paper.title}

Abstract: {paper.summary}

Focus on:
1. Main contribution
2. Relevance to AI safety/control/interpretability
3. Key findings or methods"""
                }
            ]
            
            response = self.llm_config.complete(messages, max_tokens=150, temperature=0.3)
            summary = response.choices[0].message.content.strip()
            
            return summary
        except Exception as e:
            logger.error(f"Failed to summarize paper {paper.entry_id}: {e}")
            return None
    
    def extract_arxiv_id(self, entry_id: str) -> str:
        """Extract the arXiv ID from the entry URL."""
        # Entry ID format: http://arxiv.org/abs/2312.00752v1
        match = re.search(r'(\d{4}\.\d{4,5})', entry_id)
        if match:
            return match.group(1)
        # Try newer format
        match = re.search(r'abs/(\d{4}\.\d{4,5})', entry_id)
        if match:
            return match.group(1)
        return entry_id.split('/')[-1]
    
    def store_paper(self, paper: arxiv.Result, db: Session) -> Optional[Paper]:
        """
        Store a paper in the database.
        
        Args:
            paper: arxiv.Result object
            db: Database session
            
        Returns:
            Paper object or None if already exists
        """
        arxiv_id = self.extract_arxiv_id(paper.entry_id)
        
        # Check if paper already exists
        existing = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()
        if existing:
            logger.debug(f"Paper {arxiv_id} already exists in database")
            return None
        
        # Calculate relevance score
        relevance_score, matched_keywords = self.calculate_relevance_score(paper)
        
        # Create paper record
        db_paper = Paper(
            arxiv_id=arxiv_id,
            title=paper.title,
            authors=[{"name": author.name} for author in paper.authors],
            abstract=paper.summary,
            pdf_url=paper.pdf_url,
            categories=paper.categories,
            submission_date=paper.published.date(),
            relevance_score=relevance_score,
            keyword_matches=matched_keywords
        )
        
        # Generate summary if relevance score is high enough
        if relevance_score >= float(os.getenv("MIN_RELEVANCE_SCORE", "0.6")):
            summary = self.summarize_paper(paper)
            if summary:
                db_paper.summary = summary
                db_paper.summarized = True
        
        db.add(db_paper)
        db.commit()
        db.refresh(db_paper)
        
        logger.info(f"Stored paper: {arxiv_id} - {paper.title[:50]}... (relevance: {relevance_score:.2f})")
        return db_paper
    
    def collect_papers(self, start_date: Optional[date] = None) -> Dict[str, int]:
        """
        Main method to collect and store papers.
        
        Args:
            start_date: Start date for collection
            
        Returns:
            Dictionary with collection statistics
        """
        stats = {
            "searched": 0,
            "stored": 0,
            "skipped": 0,
            "relevant": 0,
            "errors": 0
        }
        
        # Search papers
        papers = self.search_papers(start_date)
        stats["searched"] = len(papers)
        
        # Process each paper
        with get_db() as db:
            for paper in papers:
                try:
                    # Rate limiting (1 request per 3 seconds as per arXiv guidelines)
                    time.sleep(3)
                    
                    stored_paper = self.store_paper(paper, db)
                    if stored_paper:
                        stats["stored"] += 1
                        if stored_paper.relevance_score >= float(os.getenv("MIN_RELEVANCE_SCORE", "0.6")):
                            stats["relevant"] += 1
                    else:
                        stats["skipped"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing paper {paper.entry_id}: {e}")
                    stats["errors"] += 1
        
        logger.info(f"Collection complete: {stats}")
        return stats
    
    def find_papers_by_ids(self, arxiv_ids: List[str]) -> List[Paper]:
        """
        Find papers by their arXiv IDs (for cross-referencing).
        
        Args:
            arxiv_ids: List of arXiv IDs
            
        Returns:
            List of Paper objects
        """
        with get_db() as db:
            papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
            return papers
    
    def extract_arxiv_mentions(self, text: str) -> List[str]:
        """
        Extract arXiv paper IDs mentioned in text.
        
        Args:
            text: Text to search for arXiv IDs
            
        Returns:
            List of found arXiv IDs
        """
        # Common arXiv ID patterns
        patterns = [
            r'arxiv[:\s]+(\d{4}\.\d{4,5})',  # arxiv:2312.00752
            r'arXiv[:\s]+(\d{4}\.\d{4,5})',  # arXiv:2312.00752
            r'(\d{4}\.\d{4,5})',              # Just the number
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})'  # Full URL
        ]
        
        arxiv_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            arxiv_ids.extend(matches)
        
        # Remove duplicates and validate format
        valid_ids = []
        for arxiv_id in set(arxiv_ids):
            if re.match(r'^\d{4}\.\d{4,5}$', arxiv_id):
                valid_ids.append(arxiv_id)
        
        return valid_ids