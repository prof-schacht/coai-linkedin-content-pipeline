#!/usr/bin/env python3
"""
Interactive review interface for generated LinkedIn posts.
Allows manual review, editing, and approval of AI-generated content.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import init_db, get_db
from src.models.generated_post import GeneratedPost
from src.generators.visual_extractor import VisualExtractor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PostReviewer:
    """Interactive post review interface."""
    
    def __init__(self):
        self.visual_extractor = VisualExtractor()
        
    def review_pending_posts(self) -> None:
        """Review all pending posts interactively."""
        with get_db() as db:
            pending_posts = db.query(GeneratedPost).filter(
                GeneratedPost.status.in_(['draft', 'needs_review'])
            ).order_by(GeneratedPost.created_at.desc()).all()
            
            if not pending_posts:
                print("✅ No posts pending review!")
                return
            
            print(f"\n📝 Found {len(pending_posts)} posts for review\n")
            
            for i, post in enumerate(pending_posts):
                print(f"\n{'='*60}")
                print(f"Post {i+1}/{len(pending_posts)} (ID: {post.id})")
                print(f"{'='*60}")
                
                action = self._review_single_post(post)
                
                if action == 'quit':
                    print("\n👋 Review session ended")
                    break
                elif action == 'skip_all':
                    print("\n⏭️ Skipping remaining posts")
                    break
            
            # Final summary
            self._show_review_summary()
    
    def _review_single_post(self, post: GeneratedPost) -> str:
        """Review a single post and get user action."""
        
        # Display post information
        self._display_post_info(post)
        
        # Show content
        self._display_post_content(post)
        
        # Show visual if available
        self._display_visual_content(post)
        
        # Show quality metrics
        self._display_quality_metrics(post)
        
        # Get user action
        while True:
            print("\n🎯 Actions:")
            print("  [a] Approve    [e] Edit    [r] Reject    [g] Regenerate")
            print("  [s] Skip       [q] Quit    [sa] Skip All")
            
            action = input("\nChoose action: ").lower().strip()
            
            if action == 'a':
                return self._approve_post(post)
            elif action == 'e':
                return self._edit_post(post)
            elif action == 'r':
                return self._reject_post(post)
            elif action == 'g':
                return self._regenerate_post(post)
            elif action == 's':
                return 'skip'
            elif action == 'q':
                return 'quit'
            elif action == 'sa':
                return 'skip_all'
            else:
                print("❌ Invalid action. Please try again.")
    
    def _display_post_info(self, post: GeneratedPost) -> None:
        """Display basic post information."""
        print(f"📊 Created: {post.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"📊 Status: {post.status}")
        print(f"📊 Quality Score: {post.quality_score:.1f}/10" if post.quality_score else "📊 Quality Score: Not calculated")
        
        if post.paper_id:
            print(f"📄 Source: Paper ID {post.paper_id}")
        elif post.x_post_ids:
            print(f"🐦 Source: X Posts {post.x_post_ids}")
        
        if post.hashtags:
            print(f"🏷️ Hashtags: {', '.join(post.hashtags)}")
        
        if post.mentions:
            print(f"👥 Mentions: {', '.join(post.mentions)}")
    
    def _display_post_content(self, post: GeneratedPost) -> None:
        """Display the post content."""
        print(f"\n📝 Content ({len(post.content)} chars):")
        print("─" * 50)
        print(post.content)
        print("─" * 50)
    
    def _display_visual_content(self, post: GeneratedPost) -> None:
        """Display information about visual content."""
        if post.visual_path and os.path.exists(post.visual_path):
            print(f"\n🖼️ Visual: {post.visual_path}")
            
            # Try to show image info
            try:
                from PIL import Image
                with Image.open(post.visual_path) as img:
                    print(f"   Size: {img.width}x{img.height}")
                    print(f"   Format: {img.format}")
                    
                    # Check file size
                    file_size = os.path.getsize(post.visual_path)
                    print(f"   File Size: {file_size / 1024:.1f} KB")
                    
            except ImportError:
                print("   (Install PIL to see image details)")
            except Exception as e:
                print(f"   Error reading image: {e}")
        else:
            print("\n🖼️ No visual content")
    
    def _display_quality_metrics(self, post: GeneratedPost) -> None:
        """Display quality assessment."""
        print(f"\n📈 Quality Assessment:")
        
        # Content length check
        length = len(post.content)
        if length <= 3000:
            print(f"   ✅ Length: {length}/3000 chars")
        else:
            print(f"   ❌ Length: {length}/3000 chars (too long)")
        
        # Hashtag check
        if post.hashtags and len(post.hashtags) >= 2:
            print(f"   ✅ Hashtags: {len(post.hashtags)} tags")
        else:
            print(f"   ⚠️ Hashtags: {len(post.hashtags or [])} tags (needs 2+)")
        
        # Mention check
        if post.mentions:
            print(f"   ✅ Mentions: {len(post.mentions)} people")
        else:
            print(f"   ⚠️ No mentions")
        
        # Engagement elements
        question_marks = post.content.count('?')
        exclamations = post.content.count('!')
        if question_marks > 0 or exclamations > 0:
            print(f"   ✅ Engagement: {question_marks} questions, {exclamations} exclamations")
        else:
            print(f"   ⚠️ No engagement elements (questions/exclamations)")
    
    def _approve_post(self, post: GeneratedPost) -> str:
        """Approve a post."""
        post.status = 'approved'
        post.review_notes = f"Approved by reviewer on {datetime.utcnow().isoformat()}"
        
        # Set scheduling if not already set
        if not post.scheduled_for:
            # Schedule for next business day at 9 AM
            from datetime import timedelta
            next_day = datetime.utcnow().replace(hour=17, minute=0, second=0) + timedelta(days=1)  # 9 AM PST
            post.scheduled_for = next_day
            print(f"   📅 Scheduled for: {next_day.strftime('%Y-%m-%d %H:%M')}")
        
        with get_db() as db:
            db.merge(post)
            db.commit()
        
        print("✅ Post approved!")
        return 'continue'
    
    def _edit_post(self, post: GeneratedPost) -> str:
        """Allow editing of post content."""
        print("\n✏️ Edit Mode")
        print("Current content:")
        print("─" * 50)
        print(post.content)
        print("─" * 50)
        
        print("\nEnter new content (or press Enter to keep current):")
        print("(Type 'END' on a new line to finish)")
        
        new_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            new_lines.append(line)
        
        if new_lines:
            new_content = '\n'.join(new_lines).strip()
            if new_content:
                post.content = new_content
                post.review_notes = f"Edited by reviewer on {datetime.utcnow().isoformat()}"
                
                # Recalculate quality score
                self._recalculate_quality_score(post)
                
                with get_db() as db:
                    db.merge(post)
                    db.commit()
                
                print("✅ Content updated!")
                
                # Ask if they want to approve now
                approve = input("\nApprove this edited post? [y/N]: ").lower().strip()
                if approve in ['y', 'yes']:
                    return self._approve_post(post)
        
        return 'continue'
    
    def _reject_post(self, post: GeneratedPost) -> str:
        """Reject a post."""
        reason = input("\n❌ Rejection reason (optional): ").strip()
        
        post.status = 'rejected'
        post.review_notes = f"Rejected by reviewer on {datetime.utcnow().isoformat()}"
        if reason:
            post.review_notes += f" - Reason: {reason}"
        
        with get_db() as db:
            db.merge(post)
            db.commit()
        
        print("❌ Post rejected!")
        return 'continue'
    
    def _regenerate_post(self, post: GeneratedPost) -> str:
        """Mark post for regeneration."""
        print("\n🔄 Marking for regeneration...")
        
        post.status = 'needs_regeneration'
        post.review_notes = f"Marked for regeneration by reviewer on {datetime.utcnow().isoformat()}"
        
        with get_db() as db:
            db.merge(post)
            db.commit()
        
        print("🔄 Post marked for regeneration!")
        return 'continue'
    
    def _recalculate_quality_score(self, post: GeneratedPost) -> None:
        """Recalculate quality score after editing."""
        # Simple quality scoring
        quality_score = 5.0
        
        # Length check
        length = len(post.content)
        if 200 <= length <= 3000:
            quality_score += 1.5
        elif length > 3000:
            quality_score -= 2.0
        
        # Hashtag check
        if post.hashtags and len(post.hashtags) >= 2:
            quality_score += 1.0
        
        # Mention check
        if post.mentions:
            quality_score += 0.5
        
        # Engagement check
        if '?' in post.content or '!' in post.content:
            quality_score += 1.0
        
        post.quality_score = min(quality_score, 10.0)
    
    def _show_review_summary(self) -> None:
        """Show summary of review session."""
        with get_db() as db:
            # Count posts by status
            approved = db.query(GeneratedPost).filter_by(status='approved').count()
            pending = db.query(GeneratedPost).filter(
                GeneratedPost.status.in_(['draft', 'needs_review'])
            ).count()
            rejected = db.query(GeneratedPost).filter_by(status='rejected').count()
            
            print(f"\n📊 Current Status Summary:")
            print(f"   ✅ Approved: {approved}")
            print(f"   ⏳ Pending: {pending}")
            print(f"   ❌ Rejected: {rejected}")
    
    def show_scheduled_posts(self) -> None:
        """Show all scheduled posts."""
        with get_db() as db:
            scheduled_posts = db.query(GeneratedPost).filter(
                GeneratedPost.status == 'approved',
                GeneratedPost.scheduled_for.is_not(None),
                GeneratedPost.posted_at.is_(None)
            ).order_by(GeneratedPost.scheduled_for).all()
            
            if not scheduled_posts:
                print("📅 No posts currently scheduled")
                return
            
            print(f"\n📅 Scheduled Posts ({len(scheduled_posts)}):")
            print("─" * 60)
            
            for post in scheduled_posts:
                print(f"ID {post.id:3d} | {post.scheduled_for.strftime('%Y-%m-%d %H:%M')} | "
                      f"Score: {post.quality_score:.1f} | "
                      f"{len(post.content):3d} chars")
                print(f"      Content: {post.content[:60]}...")
                print()
    
    def quick_approve_high_quality(self, min_score: float = 8.0) -> None:
        """Quick approve posts above quality threshold."""
        with get_db() as db:
            high_quality_posts = db.query(GeneratedPost).filter(
                GeneratedPost.status == 'draft',
                GeneratedPost.quality_score >= min_score
            ).all()
            
            if not high_quality_posts:
                print(f"📝 No posts with quality score >= {min_score}")
                return
            
            print(f"\n🚀 Auto-approving {len(high_quality_posts)} high-quality posts...")
            
            for post in high_quality_posts:
                post.status = 'approved'
                post.review_notes = f"Auto-approved (score: {post.quality_score:.1f}) on {datetime.utcnow().isoformat()}"
                
                # Schedule if not already scheduled
                if not post.scheduled_for:
                    from datetime import timedelta
                    next_slot = datetime.utcnow().replace(hour=17, minute=0, second=0) + timedelta(days=1)
                    post.scheduled_for = next_slot
                
                db.merge(post)
                print(f"   ✅ Post {post.id} (score: {post.quality_score:.1f})")
            
            db.commit()
            print(f"\n✅ Auto-approved {len(high_quality_posts)} posts!")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Interactive LinkedIn post review interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review all pending posts
  python scripts/review_posts.py
  
  # Show scheduled posts
  python scripts/review_posts.py --show-scheduled
  
  # Auto-approve high-quality posts
  python scripts/review_posts.py --auto-approve --min-score 8.5
        """
    )
    
    parser.add_argument(
        '--show-scheduled',
        action='store_true',
        help='Show currently scheduled posts'
    )
    parser.add_argument(
        '--auto-approve',
        action='store_true',
        help='Auto-approve posts above quality threshold'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=8.0,
        help='Minimum quality score for auto-approval (default: 8.0)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Create reviewer
    reviewer = PostReviewer()
    
    try:
        if args.show_scheduled:
            reviewer.show_scheduled_posts()
        elif args.auto_approve:
            reviewer.quick_approve_high_quality(args.min_score)
        else:
            # Interactive review
            print("🎯 COAI LinkedIn Post Review Interface")
            print("=" * 50)
            reviewer.review_pending_posts()
            
    except KeyboardInterrupt:
        print("\n\n👋 Review interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Review failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())