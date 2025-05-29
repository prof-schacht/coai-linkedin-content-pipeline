#!/usr/bin/env python3
"""
Comprehensive test script for the content pipeline and monitoring system.
Tests all components of Issues #6 and #7.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import init_db, get_db
from src.models.generated_post import GeneratedPost
from src.generators.content_scorer import ContentScorer, ContentOpportunity
from src.generators.post_creator import ContentPipeline
from src.utils.cost_tracker import CostTracker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_content_scoring():
    """Test the content scoring system."""
    print("\n🎯 Testing Content Scoring System...")
    
    try:
        scorer = ContentScorer()
        
        # Test scoring recent content
        opportunities = scorer.score_recent_content(days=30)
        print(f"   ✅ Found {len(opportunities)} content opportunities")
        
        # Test getting top opportunities
        top_opportunities = scorer.get_top_opportunities(count=3, days=30)
        print(f"   ✅ Selected {len(top_opportunities)} top opportunities")
        
        if top_opportunities:
            best = top_opportunities[0]
            print(f"   📊 Best opportunity: {best.title[:50]}... (Score: {best.total_score:.1f})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Content scoring failed: {e}")
        return False


async def test_pipeline_orchestrator():
    """Test the main pipeline orchestrator."""
    print("\n🚀 Testing Pipeline Orchestrator...")
    
    try:
        pipeline = ContentPipeline()
        
        # Test pipeline statistics
        stats = pipeline.get_pipeline_stats(7)
        print(f"   ✅ Pipeline stats: {stats['total_posts_generated']} posts generated")
        print(f"   📊 Approval rate: {stats['approval_rate']:.1%}")
        print(f"   ⭐ Average quality: {stats['average_quality_score']}")
        
        # Test emergency post generation
        print("   🚨 Testing emergency post generation...")
        emergency_post = await pipeline.generate_emergency_post(
            topic="AI Safety Breakthrough",
            urgency="high"
        )
        
        if emergency_post:
            print(f"   ✅ Emergency post created (ID: {emergency_post.id})")
        else:
            print("   ⚠️ Emergency post not created (may be due to quality threshold)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Pipeline orchestrator failed: {e}")
        return False


def test_cost_tracking():
    """Test the cost tracking system."""
    print("\n💰 Testing Cost Tracking System...")
    
    try:
        tracker = CostTracker()
        
        # Test tracking a mock LLM call
        result = tracker.track_llm_call(
            model="ollama/deepseek-r1:1.5b",
            input_tokens=100,
            output_tokens=50,
            component="test_pipeline",
            request_type="completion",
            latency_ms=500,
            success=True
        )
        
        print(f"   ✅ Tracked LLM call: ${result['total_cost']:.6f}")
        
        # Test usage statistics
        stats = tracker.get_usage_stats(30)
        print(f"   📊 Total requests (30d): {stats['total_requests']}")
        print(f"   💵 Total cost (30d): ${stats['total_cost']:.4f}")
        print(f"   🎯 Success rate: {stats['success_rate']:.1%}")
        
        # Test monthly costs
        monthly = tracker.get_monthly_costs()
        print(f"   📅 Monthly cost: ${monthly['current_month_cost']:.4f}")
        print(f"   📊 Budget usage: {monthly['budget_usage_percent']:.1%}")
        
        # Test recommendations
        recommendations = tracker.get_model_recommendations()
        print(f"   💡 Recommendations: {len(recommendations)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Cost tracking failed: {e}")
        return False


def test_post_generation():
    """Test post generation and storage."""
    print("\n📝 Testing Post Generation...")
    
    try:
        with get_db() as db:
            # Create a test post
            test_post = GeneratedPost(
                content="This is a test LinkedIn post about AI safety research. "
                       "It demonstrates the importance of alignment and interpretability. "
                       "What are your thoughts on the latest developments? #AISafety #MechanisticInterpretability",
                hashtags=["#AISafety", "#MechanisticInterpretability"],
                mentions=["@TestUser"],
                quality_score=8.5,
                status="draft",
                engagement_prediction=0.85
            )
            
            db.add(test_post)
            db.commit()
            db.refresh(test_post)
            
            print(f"   ✅ Created test post (ID: {test_post.id})")
            print(f"   📊 Quality score: {test_post.quality_score}")
            print(f"   📏 Content length: {len(test_post.content)} chars")
            print(f"   🏷️ Hashtags: {len(test_post.hashtags)} tags")
            print(f"   👥 Mentions: {len(test_post.mentions)} people")
            
            # Test post properties
            print(f"   ✅ Ready to post: {test_post.is_ready_to_post}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Post generation failed: {e}")
        return False


def test_database_connectivity():
    """Test database connectivity and models."""
    print("\n🗄️ Testing Database Connectivity...")
    
    try:
        # Test connection
        init_db()
        print("   ✅ Database connection successful")
        
        # Test table existence
        with get_db() as db:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            required_tables = [
                'papers', 'x_posts', 'linkedin_connections', 
                'generated_posts', 'post_analytics', 'cost_records'
            ]
            
            missing_tables = []
            for table in required_tables:
                if table in tables:
                    print(f"   ✅ Table '{table}' exists")
                else:
                    missing_tables.append(table)
                    print(f"   ❌ Table '{table}' missing")
            
            if missing_tables:
                print(f"   ⚠️ Missing tables: {missing_tables}")
                return False
            
            # Test basic queries
            post_count = db.query(GeneratedPost).count()
            print(f"   📊 Generated posts in database: {post_count}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Database connectivity failed: {e}")
        return False


def test_visual_extraction():
    """Test visual content extraction capabilities."""
    print("\n🖼️ Testing Visual Content Extraction...")
    
    try:
        from src.generators.visual_extractor import VisualExtractor
        
        extractor = VisualExtractor()
        
        # Test quote card creation
        quote_card = extractor.create_quote_card(
            text="AI safety research is crucial for ensuring that artificial general intelligence systems remain aligned with human values.",
            author="COAI Research Team",
            source="Research Brief 2024",
            theme="professional"
        )
        
        if quote_card:
            print(f"   ✅ Quote card created: {quote_card['filename']}")
            print(f"   📏 Dimensions: {quote_card['width']}x{quote_card['height']}")
            print(f"   💾 File size: {quote_card['file_size']} bytes")
        else:
            print("   ⚠️ Quote card creation skipped (PIL not available)")
        
        # Test visual cleanup
        cleaned = extractor.cleanup_old_visuals(days=30)
        print(f"   🧹 Cleaned up {cleaned} old visual files")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Visual extraction failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("🧪 COAI Content Pipeline - Comprehensive Test Suite")
    print("=" * 60)
    
    test_results = {}
    
    # Database tests
    test_results['database'] = test_database_connectivity()
    
    # Content scoring tests
    test_results['content_scoring'] = await test_content_scoring()
    
    # Post generation tests
    test_results['post_generation'] = test_post_generation()
    
    # Pipeline orchestrator tests
    test_results['pipeline'] = await test_pipeline_orchestrator()
    
    # Cost tracking tests
    test_results['cost_tracking'] = test_cost_tracking()
    
    # Visual extraction tests
    test_results['visual_extraction'] = test_visual_extraction()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("-" * 30)
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Pipeline is ready for production.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False


async def main():
    """Main execution function."""
    try:
        success = await run_comprehensive_tests()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
        return 0
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))