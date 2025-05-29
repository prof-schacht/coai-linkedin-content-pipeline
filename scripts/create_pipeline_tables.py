#!/usr/bin/env python3
"""
Create database tables for the pipeline and monitoring system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import init_db, engine, Base
from src.models.generated_post import GeneratedPost, PostAnalytics, ContentTemplate
from src.utils.cost_tracker import CostRecord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_tables():
    """Create all pipeline and monitoring tables."""
    
    print("🗄️ Creating pipeline and monitoring tables...")
    
    try:
        # Initialize database connection
        init_db()
        
        # Import all models to ensure they're registered
        from src.models.paper import Paper
        from src.models.x_post import XPost
        from src.models.linkedin_connection import LinkedInConnection, ExpertiseMapping
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Tables created successfully!")
        
        # List created tables
        print("\n📋 Created tables:")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        pipeline_tables = [
            'generated_posts', 'post_analytics', 'content_templates', 'cost_records'
        ]
        
        for table in pipeline_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (missing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


if __name__ == "__main__":
    if create_tables():
        print("\n🎉 Pipeline tables setup complete!")
        sys.exit(0)
    else:
        print("\n💥 Table creation failed!")
        sys.exit(1)