#!/usr/bin/env python3
"""
COAI Content Pipeline Monitoring Dashboard
Real-time monitoring and analytics for the LinkedIn content generation system.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import init_db, get_db
from src.models.generated_post import GeneratedPost, PostAnalytics
from src.models.paper import Paper
from src.models.x_post import XPost
from src.models.linkedin_connection import LinkedInConnection
from src.utils.cost_tracker import CostTracker
from src.generators.post_creator import ContentPipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Dashboard:
    """Real-time monitoring dashboard for the content pipeline."""
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.pipeline = ContentPipeline()
        
    def display_main_dashboard(self, refresh_interval: int = 30) -> None:
        """Display the main dashboard with auto-refresh."""
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Header
                self._print_header()
                
                # Main sections
                self._display_pipeline_status()
                self._display_content_stats()
                self._display_cost_summary()
                self._display_performance_metrics()
                self._display_recent_activity()
                self._display_alerts()
                
                # Footer
                self._print_footer(refresh_interval)
                
                # Wait for refresh or user input
                if refresh_interval > 0:
                    time.sleep(refresh_interval)
                else:
                    input("\nPress Enter to refresh...")
                    
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped")
    
    def _print_header(self) -> None:
        """Print dashboard header."""
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        print("=" * 80)
        print("🚀 COAI CONTENT PIPELINE DASHBOARD")
        print(f"⏰ Last Updated: {now}")
        print("=" * 80)
    
    def _display_pipeline_status(self) -> None:
        """Display current pipeline status."""
        print("\n📊 PIPELINE STATUS")
        print("-" * 40)
        
        with get_db() as db:
            # Today's activity
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            posts_generated_today = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= today_start
            ).count()
            
            posts_approved_today = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= today_start,
                GeneratedPost.status == 'approved'
            ).count()
            
            posts_scheduled = db.query(GeneratedPost).filter(
                GeneratedPost.status == 'approved',
                GeneratedPost.scheduled_for.is_not(None),
                GeneratedPost.posted_at.is_(None)
            ).count()
            
            posts_pending_review = db.query(GeneratedPost).filter(
                GeneratedPost.status.in_(['draft', 'needs_review'])
            ).count()
            
            # Recent papers and posts
            papers_today = db.query(Paper).filter(
                Paper.created_at >= today_start
            ).count()
            
            x_posts_today = db.query(XPost).filter(
                XPost.created_at >= today_start
            ).count()
            
        # Status indicators
        status_icon = "🟢" if posts_generated_today > 0 else "🟡"
        
        print(f"{status_icon} Pipeline Status: {'ACTIVE' if posts_generated_today > 0 else 'IDLE'}")
        print(f"📝 Posts Generated Today: {posts_generated_today}")
        print(f"✅ Posts Approved Today: {posts_approved_today}")
        print(f"📅 Posts Scheduled: {posts_scheduled}")
        print(f"⏳ Pending Review: {posts_pending_review}")
        print(f"📄 Papers Collected Today: {papers_today}")
        print(f"🐦 X Posts Collected Today: {x_posts_today}")
    
    def _display_content_stats(self) -> None:
        """Display content generation statistics."""
        print("\n📈 CONTENT STATISTICS (Last 7 Days)")
        print("-" * 45)
        
        pipeline_stats = self.pipeline.get_pipeline_stats(7)
        
        print(f"📊 Total Posts Generated: {pipeline_stats['total_posts_generated']}")
        print(f"✅ Approval Rate: {pipeline_stats['approval_rate']:.1%}")
        print(f"🎯 Average Quality Score: {pipeline_stats['average_quality_score']}")
        print(f"📅 Posts Per Day: {pipeline_stats['posts_per_day']:.1f}")
        print(f"📤 Posts Published: {pipeline_stats['posts_published']}")
        
        # Quality distribution
        with get_db() as db:
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            high_quality = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= week_ago,
                GeneratedPost.quality_score >= 8.0
            ).count()
            
            medium_quality = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= week_ago,
                GeneratedPost.quality_score >= 6.0,
                GeneratedPost.quality_score < 8.0
            ).count()
            
            low_quality = db.query(GeneratedPost).filter(
                GeneratedPost.created_at >= week_ago,
                GeneratedPost.quality_score < 6.0
            ).count()
            
        print(f"🌟 Quality Distribution: High: {high_quality} | Medium: {medium_quality} | Low: {low_quality}")
    
    def _display_cost_summary(self) -> None:
        """Display cost tracking summary."""
        print("\n💰 COST TRACKING")
        print("-" * 25)
        
        # Monthly costs
        monthly_info = self.cost_tracker.get_monthly_costs()
        usage_stats = self.cost_tracker.get_usage_stats(30)
        
        # Budget status indicator
        if monthly_info['is_over_budget']:
            budget_icon = "🔴"
            budget_status = "OVER BUDGET"
        elif monthly_info['is_over_threshold']:
            budget_icon = "🟡"
            budget_status = "APPROACHING LIMIT"
        else:
            budget_icon = "🟢"
            budget_status = "ON TRACK"
        
        print(f"{budget_icon} Budget Status: {budget_status}")
        print(f"💵 This Month: ${monthly_info['current_month_cost']:.2f} / ${monthly_info['monthly_budget']:.2f}")
        print(f"📊 Budget Used: {monthly_info['budget_usage_percent']:.1%}")
        print(f"📈 Projected: ${monthly_info['projected_monthly_cost']:.2f}")
        print(f"💱 Daily Average: ${monthly_info['daily_average']:.2f}")
        print(f"🔢 Total Requests (30d): {usage_stats['total_requests']:,}")
        print(f"🎯 Success Rate: {usage_stats['success_rate']:.1%}")
        
        # Top models by cost
        if usage_stats['model_breakdown']:
            top_model = max(usage_stats['model_breakdown'], key=lambda x: x['cost'])
            print(f"💸 Top Cost Model: {top_model['model']} (${top_model['cost']:.4f})")
    
    def _display_performance_metrics(self) -> None:
        """Display system performance metrics."""
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 30)
        
        usage_stats = self.cost_tracker.get_usage_stats(7)
        
        print(f"⏱️  Avg Response Time: {usage_stats['avg_latency_ms']:.0f}ms")
        print(f"🎯 Success Rate: {usage_stats['success_rate']:.1%}")
        print(f"💰 Avg Cost per Request: ${usage_stats['avg_cost_per_request']:.6f}")
        print(f"🔤 Total Tokens (7d): {usage_stats['total_tokens']:,}")
        
        # Check for performance issues
        if usage_stats['avg_latency_ms'] > 5000:
            print("⚠️  High latency detected!")
        
        if usage_stats['success_rate'] < 0.95:
            print("⚠️  Low success rate!")
    
    def _display_recent_activity(self) -> None:
        """Display recent system activity."""
        print("\n🕒 RECENT ACTIVITY")
        print("-" * 25)
        
        with get_db() as db:
            # Recent posts
            recent_posts = db.query(GeneratedPost).order_by(
                GeneratedPost.created_at.desc()
            ).limit(3).all()
            
            if recent_posts:
                print("📝 Recent Posts:")
                for post in recent_posts:
                    age = datetime.utcnow() - post.created_at
                    age_str = self._format_time_ago(age)
                    status_icon = {"approved": "✅", "draft": "📝", "rejected": "❌"}.get(post.status, "❓")
                    print(f"   {status_icon} {age_str}: Score {post.quality_score:.1f} | {post.status}")
            
            # Recent papers
            recent_papers = db.query(Paper).order_by(
                Paper.created_at.desc()
            ).limit(2).all()
            
            if recent_papers:
                print("📄 Recent Papers:")
                for paper in recent_papers:
                    age = datetime.utcnow() - paper.created_at
                    age_str = self._format_time_ago(age)
                    print(f"   📄 {age_str}: {paper.arxiv_id} (Score: {paper.relevance_score:.2f})")
    
    def _display_alerts(self) -> None:
        """Display system alerts and recommendations."""
        alerts = []
        
        # Budget alerts
        monthly_info = self.cost_tracker.get_monthly_costs()
        if monthly_info['is_over_budget']:
            alerts.append("🔴 Monthly budget exceeded!")
        elif monthly_info['is_over_threshold']:
            alerts.append("🟡 Approaching monthly budget limit")
        
        # Performance alerts
        usage_stats = self.cost_tracker.get_usage_stats(1)  # Last day
        if usage_stats['success_rate'] < 0.9:
            alerts.append("🟡 Low API success rate detected")
        
        # Content alerts
        with get_db() as db:
            pending_review = db.query(GeneratedPost).filter(
                GeneratedPost.status.in_(['draft', 'needs_review'])
            ).count()
            
            if pending_review > 5:
                alerts.append(f"🟡 {pending_review} posts pending review")
            
            # Check for old scheduled posts
            old_scheduled = db.query(GeneratedPost).filter(
                GeneratedPost.status == 'approved',
                GeneratedPost.scheduled_for < datetime.utcnow() - timedelta(hours=1),
                GeneratedPost.posted_at.is_(None)
            ).count()
            
            if old_scheduled > 0:
                alerts.append(f"🔴 {old_scheduled} posts missed scheduled time!")
        
        # Recommendations
        recommendations = self.cost_tracker.get_model_recommendations()
        for rec in recommendations[:2]:  # Show top 2
            if rec['priority'] == 'high':
                alerts.append(f"💡 {rec['message']}")
        
        if alerts:
            print("\n🚨 ALERTS & RECOMMENDATIONS")
            print("-" * 35)
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("\n✅ No active alerts")
    
    def _print_footer(self, refresh_interval: int) -> None:
        """Print dashboard footer."""
        print("\n" + "-" * 80)
        if refresh_interval > 0:
            print(f"🔄 Auto-refreshing every {refresh_interval}s | Press Ctrl+C to exit")
        else:
            print("📊 Manual refresh mode | Press Enter to refresh | Ctrl+C to exit")
    
    def _format_time_ago(self, delta: timedelta) -> str:
        """Format time delta as human readable string."""
        total_seconds = int(delta.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"
    
    def generate_detailed_report(self) -> str:
        """Generate a detailed system report."""
        report_lines = [
            "# COAI Content Pipeline Detailed Report",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
        ]
        
        # Pipeline stats
        pipeline_stats = self.pipeline.get_pipeline_stats(30)
        report_lines.extend([
            "## Pipeline Performance (30 days)",
            f"- Posts Generated: {pipeline_stats['total_posts_generated']}",
            f"- Approval Rate: {pipeline_stats['approval_rate']:.1%}",
            f"- Average Quality: {pipeline_stats['average_quality_score']}/10",
            f"- Posts per Day: {pipeline_stats['posts_per_day']:.1f}",
            "",
        ])
        
        # Cost analysis
        monthly_info = self.cost_tracker.get_monthly_costs()
        usage_stats = self.cost_tracker.get_usage_stats(30)
        report_lines.extend([
            "## Cost Analysis",
            f"- Monthly Cost: ${monthly_info['current_month_cost']:.4f}",
            f"- Budget: ${monthly_info['monthly_budget']:.2f}",
            f"- Budget Usage: {monthly_info['budget_usage_percent']:.1%}",
            f"- Total Requests: {usage_stats['total_requests']:,}",
            f"- Success Rate: {usage_stats['success_rate']:.1%}",
            "",
        ])
        
        # Model breakdown
        if usage_stats['model_breakdown']:
            report_lines.extend([
                "## Model Usage",
            ])
            for model in usage_stats['model_breakdown']:
                report_lines.append(
                    f"- {model['model']}: ${model['cost']:.4f} | "
                    f"{model['requests']} requests | {model['tokens']:,} tokens"
                )
            report_lines.append("")
        
        # Content analysis
        with get_db() as db:
            # Post status breakdown
            total_posts = db.query(GeneratedPost).count()
            approved = db.query(GeneratedPost).filter_by(status='approved').count()
            pending = db.query(GeneratedPost).filter(
                GeneratedPost.status.in_(['draft', 'needs_review'])
            ).count()
            rejected = db.query(GeneratedPost).filter_by(status='rejected').count()
            
            report_lines.extend([
                "## Content Statistics",
                f"- Total Posts: {total_posts}",
                f"- Approved: {approved} ({approved/max(total_posts,1):.1%})",
                f"- Pending: {pending}",
                f"- Rejected: {rejected}",
                "",
            ])
        
        # Recommendations
        recommendations = self.cost_tracker.get_model_recommendations()
        if recommendations:
            report_lines.extend([
                "## Recommendations",
            ])
            for rec in recommendations:
                report_lines.append(f"- {rec['message']}")
        
        return "\n".join(report_lines)
    
    def export_csv_data(self, output_dir: str = "exports") -> List[str]:
        """Export dashboard data to CSV files."""
        import csv
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        exported_files = []
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Export posts data
        posts_file = output_path / f"posts_{timestamp}.csv"
        with open(posts_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'created_at', 'status', 'quality_score', 'content_length',
                'scheduled_for', 'posted_at', 'engagement_prediction'
            ])
            
            with get_db() as db:
                posts = db.query(GeneratedPost).all()
                for post in posts:
                    writer.writerow([
                        post.id,
                        post.created_at.isoformat(),
                        post.status,
                        post.quality_score,
                        len(post.content) if post.content else 0,
                        post.scheduled_for.isoformat() if post.scheduled_for else '',
                        post.posted_at.isoformat() if post.posted_at else '',
                        post.engagement_prediction
                    ])
        
        exported_files.append(str(posts_file))
        
        # Export cost data
        cost_file = output_path / f"costs_{timestamp}.csv"
        usage_stats = self.cost_tracker.get_usage_stats(30)
        
        with open(cost_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['model', 'provider', 'requests', 'cost', 'tokens'])
            
            for model in usage_stats['model_breakdown']:
                writer.writerow([
                    model['model'],
                    model['provider'],
                    model['requests'],
                    model['cost'],
                    model['tokens']
                ])
        
        exported_files.append(str(cost_file))
        
        return exported_files


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="COAI Content Pipeline Monitoring Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live dashboard with auto-refresh
  python scripts/dashboard.py
  
  # Manual refresh mode
  python scripts/dashboard.py --manual
  
  # Generate detailed report
  python scripts/dashboard.py --report
  
  # Export data to CSV
  python scripts/dashboard.py --export
        """
    )
    
    parser.add_argument(
        '--manual',
        action='store_true',
        help='Manual refresh mode (no auto-refresh)'
    )
    parser.add_argument(
        '--refresh-interval',
        type=int,
        default=30,
        help='Auto-refresh interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed text report'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export data to CSV files'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        init_db()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Create dashboard
    dashboard = Dashboard()
    
    try:
        if args.report:
            print("📊 Generating detailed report...")
            report = dashboard.generate_detailed_report()
            print(report)
            
            # Optionally save to file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"pipeline_report_{timestamp}.md"
            with open(filename, 'w') as f:
                f.write(report)
            print(f"\n💾 Report saved to: {filename}")
            
        elif args.export:
            print("📊 Exporting data to CSV...")
            files = dashboard.export_csv_data()
            print("✅ Exported files:")
            for file in files:
                print(f"   📄 {file}")
                
        else:
            # Live dashboard
            refresh_interval = 0 if args.manual else args.refresh_interval
            dashboard.display_main_dashboard(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())