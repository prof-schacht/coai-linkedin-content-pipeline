"""
Cost tracking system for monitoring LLM usage and expenses.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Boolean, Text
from sqlalchemy.sql import func
from src.models.base import Base, get_db

logger = logging.getLogger(__name__)


class CostRecord(Base):
    """Database record for tracking LLM costs."""
    
    __tablename__ = 'cost_records'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Model information
    model_name = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # ollama, openai, anthropic, etc.
    
    # Usage metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost information
    input_cost = Column(Float, default=0.0)
    output_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Request metadata
    request_type = Column(String(50), nullable=True)  # completion, chat, embedding
    component = Column(String(100), nullable=True)  # which part of system used it
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, default=func.now(), index=True)
    
    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token."""
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost / self.total_tokens


@dataclass
class ModelPricing:
    """Pricing information for a model."""
    
    model_name: str
    provider: str
    input_cost_per_token: float
    output_cost_per_token: float
    is_free: bool = False
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Tuple[float, float, float]:
        """Calculate cost for given token usage."""
        if self.is_free:
            return 0.0, 0.0, 0.0
        
        input_cost = input_tokens * self.input_cost_per_token
        output_cost = output_tokens * self.output_cost_per_token
        total_cost = input_cost + output_cost
        
        return input_cost, output_cost, total_cost


class CostTracker:
    """Tracks and monitors LLM usage costs."""
    
    def __init__(self):
        # Model pricing (per token costs in USD)
        self.model_pricing = {
            # Ollama models (free)
            'ollama/deepseek-r1:1.5b': ModelPricing('deepseek-r1:1.5b', 'ollama', 0, 0, True),
            'ollama/qwen3:8b': ModelPricing('qwen3:8b', 'ollama', 0, 0, True),
            'ollama/qwen3:14b': ModelPricing('qwen3:14b', 'ollama', 0, 0, True),
            'ollama/gemma3:27b': ModelPricing('gemma3:27b', 'ollama', 0, 0, True),
            'ollama/llama3.1:8b': ModelPricing('llama3.1:8b', 'ollama', 0, 0, True),
            'ollama/llama3.1:70b': ModelPricing('llama3.1:70b', 'ollama', 0, 0, True),
            'ollama/mistral-nemo:latest': ModelPricing('mistral-nemo', 'ollama', 0, 0, True),
            
            # OpenAI models
            'gpt-3.5-turbo': ModelPricing('gpt-3.5-turbo', 'openai', 0.0015/1000, 0.002/1000),
            'gpt-4': ModelPricing('gpt-4', 'openai', 0.03/1000, 0.06/1000),
            'gpt-4-turbo': ModelPricing('gpt-4-turbo', 'openai', 0.01/1000, 0.03/1000),
            'gpt-4o': ModelPricing('gpt-4o', 'openai', 0.005/1000, 0.015/1000),
            
            # Anthropic models
            'claude-3-sonnet': ModelPricing('claude-3-sonnet', 'anthropic', 0.003/1000, 0.015/1000),
            'claude-3-opus': ModelPricing('claude-3-opus', 'anthropic', 0.015/1000, 0.075/1000),
            'claude-3-haiku': ModelPricing('claude-3-haiku', 'anthropic', 0.00025/1000, 0.00125/1000),
            
            # Google models
            'gemini-pro': ModelPricing('gemini-pro', 'google', 0.0005/1000, 0.0015/1000),
            'gemini-pro-vision': ModelPricing('gemini-pro-vision', 'google', 0.0005/1000, 0.0015/1000),
        }
        
        # Budget settings
        self.monthly_budget = float(os.getenv('MONTHLY_BUDGET_USD', '100'))
        self.alert_threshold = float(os.getenv('COST_ALERT_THRESHOLD', '0.8'))
        
    def track_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        component: str = None,
        request_type: str = 'completion',
        latency_ms: int = None,
        success: bool = True,
        error_message: str = None
    ) -> Dict[str, any]:
        """
        Track an LLM API call and its cost.
        
        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            component: Which component made the request
            request_type: Type of request (completion, chat, embedding)
            latency_ms: Request latency in milliseconds
            success: Whether the request succeeded
            error_message: Error message if failed
            
        Returns:
            Dictionary with cost information
        """
        try:
            # Get pricing info
            pricing = self.model_pricing.get(model)
            if not pricing:
                logger.warning(f"No pricing info for model: {model}")
                pricing = ModelPricing(model, 'unknown', 0, 0)
            
            # Calculate costs
            total_tokens = input_tokens + output_tokens
            input_cost, output_cost, total_cost = pricing.calculate_cost(input_tokens, output_tokens)
            
            # Round costs to 6 decimal places
            input_cost = float(Decimal(str(input_cost)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
            output_cost = float(Decimal(str(output_cost)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
            total_cost = float(Decimal(str(total_cost)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
            
            # Store record
            with get_db() as db:
                record = CostRecord(
                    model_name=model,
                    provider=pricing.provider,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    total_cost=total_cost,
                    request_type=request_type,
                    component=component,
                    latency_ms=latency_ms,
                    success=success,
                    error_message=error_message
                )
                
                db.add(record)
                db.commit()
                db.refresh(record)
            
            # Check for budget alerts
            self._check_budget_alerts(total_cost)
            
            result = {
                'record_id': record.id,
                'model': model,
                'provider': pricing.provider,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': total_cost,
                'is_free': pricing.is_free,
                'success': success
            }
            
            logger.debug(f"Tracked LLM call: {model} - ${total_cost:.6f}")
            return result
            
        except Exception as e:
            logger.error(f"Cost tracking failed: {e}")
            return {'error': str(e), 'success': False}
    
    def get_usage_stats(self, days: int = 30) -> Dict[str, any]:
        """Get usage statistics for the specified period."""
        
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic stats
            total_records = db.query(CostRecord).filter(
                CostRecord.created_at >= cutoff_date
            ).count()
            
            successful_records = db.query(CostRecord).filter(
                CostRecord.created_at >= cutoff_date,
                CostRecord.success == True
            ).count()
            
            # Cost totals
            cost_query = db.query(
                func.sum(CostRecord.total_cost).label('total_cost'),
                func.sum(CostRecord.input_tokens).label('total_input_tokens'),
                func.sum(CostRecord.output_tokens).label('total_output_tokens'),
                func.avg(CostRecord.latency_ms).label('avg_latency')
            ).filter(
                CostRecord.created_at >= cutoff_date,
                CostRecord.success == True
            )
            
            cost_result = cost_query.first()
            
            # Model breakdown
            model_stats = db.query(
                CostRecord.model_name,
                CostRecord.provider,
                func.count(CostRecord.id).label('request_count'),
                func.sum(CostRecord.total_cost).label('total_cost'),
                func.sum(CostRecord.total_tokens).label('total_tokens'),
                func.avg(CostRecord.latency_ms).label('avg_latency')
            ).filter(
                CostRecord.created_at >= cutoff_date,
                CostRecord.success == True
            ).group_by(
                CostRecord.model_name, CostRecord.provider
            ).all()
            
            # Component breakdown
            component_stats = db.query(
                CostRecord.component,
                func.count(CostRecord.id).label('request_count'),
                func.sum(CostRecord.total_cost).label('total_cost'),
                func.sum(CostRecord.total_tokens).label('total_tokens')
            ).filter(
                CostRecord.created_at >= cutoff_date,
                CostRecord.success == True,
                CostRecord.component.is_not(None)
            ).group_by(CostRecord.component).all()
            
            # Daily breakdown
            daily_stats = db.query(
                func.date(CostRecord.created_at).label('date'),
                func.sum(CostRecord.total_cost).label('daily_cost'),
                func.count(CostRecord.id).label('daily_requests')
            ).filter(
                CostRecord.created_at >= cutoff_date,
                CostRecord.success == True
            ).group_by(
                func.date(CostRecord.created_at)
            ).order_by(
                func.date(CostRecord.created_at)
            ).all()
            
            return {
                'period_days': days,
                'total_requests': total_records,
                'successful_requests': successful_records,
                'success_rate': successful_records / max(total_records, 1),
                'total_cost': float(cost_result.total_cost or 0),
                'total_input_tokens': int(cost_result.total_input_tokens or 0),
                'total_output_tokens': int(cost_result.total_output_tokens or 0),
                'total_tokens': int((cost_result.total_input_tokens or 0) + (cost_result.total_output_tokens or 0)),
                'avg_latency_ms': float(cost_result.avg_latency or 0),
                'avg_cost_per_request': float(cost_result.total_cost or 0) / max(successful_records, 1),
                'model_breakdown': [
                    {
                        'model': stat.model_name,
                        'provider': stat.provider,
                        'requests': stat.request_count,
                        'cost': float(stat.total_cost),
                        'tokens': int(stat.total_tokens),
                        'avg_latency': float(stat.avg_latency or 0)
                    }
                    for stat in model_stats
                ],
                'component_breakdown': [
                    {
                        'component': stat.component,
                        'requests': stat.request_count,
                        'cost': float(stat.total_cost),
                        'tokens': int(stat.total_tokens)
                    }
                    for stat in component_stats
                ],
                'daily_breakdown': [
                    {
                        'date': stat.date.isoformat(),
                        'cost': float(stat.daily_cost),
                        'requests': stat.daily_requests
                    }
                    for stat in daily_stats
                ]
            }
    
    def get_monthly_costs(self) -> Dict[str, any]:
        """Get current month's cost information."""
        
        # Current month start
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        with get_db() as db:
            monthly_cost = db.query(
                func.sum(CostRecord.total_cost)
            ).filter(
                CostRecord.created_at >= month_start,
                CostRecord.success == True
            ).scalar() or 0
            
            monthly_cost = float(monthly_cost)
            
            # Calculate projections
            days_passed = (now - month_start).days + 1
            days_in_month = 30  # Approximate
            
            daily_average = monthly_cost / days_passed
            projected_monthly = daily_average * days_in_month
            
            remaining_budget = self.monthly_budget - monthly_cost
            budget_usage_percent = monthly_cost / self.monthly_budget
            
            return {
                'current_month_cost': monthly_cost,
                'monthly_budget': self.monthly_budget,
                'remaining_budget': remaining_budget,
                'budget_usage_percent': budget_usage_percent,
                'daily_average': daily_average,
                'projected_monthly_cost': projected_monthly,
                'days_passed': days_passed,
                'alert_threshold': self.alert_threshold,
                'is_over_threshold': budget_usage_percent >= self.alert_threshold,
                'is_over_budget': monthly_cost >= self.monthly_budget
            }
    
    def _check_budget_alerts(self, new_cost: float) -> None:
        """Check if we should send budget alerts."""
        monthly_info = self.get_monthly_costs()
        
        # Alert if over threshold
        if monthly_info['is_over_threshold'] and new_cost > 0:
            logger.warning(
                f"Budget alert: {monthly_info['budget_usage_percent']:.1%} of monthly budget used "
                f"(${monthly_info['current_month_cost']:.2f} / ${self.monthly_budget:.2f})"
            )
        
        # Critical alert if over budget
        if monthly_info['is_over_budget']:
            logger.error(
                f"Budget exceeded! ${monthly_info['current_month_cost']:.2f} / ${self.monthly_budget:.2f}"
            )
    
    def get_model_recommendations(self) -> List[Dict[str, any]]:
        """Get recommendations for cost optimization."""
        stats = self.get_usage_stats(30)
        recommendations = []
        
        # Analyze model usage
        model_breakdown = stats['model_breakdown']
        model_breakdown.sort(key=lambda x: x['cost'], reverse=True)
        
        for model_stat in model_breakdown:
            if model_stat['cost'] > 10:  # Models costing >$10/month
                # Check if there's a cheaper alternative
                if model_stat['provider'] != 'ollama':
                    recommendations.append({
                        'type': 'cost_optimization',
                        'priority': 'high',
                        'message': f"Consider using Ollama model instead of {model_stat['model']} "
                                 f"(saves ${model_stat['cost']:.2f}/month)",
                        'current_model': model_stat['model'],
                        'alternative': 'ollama/deepseek-r1:1.5b'
                    })
        
        # Check for high latency models
        for model_stat in model_breakdown:
            if model_stat['avg_latency'] > 5000:  # >5 seconds
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'message': f"{model_stat['model']} has high latency ({model_stat['avg_latency']:.0f}ms). "
                             f"Consider switching to a faster model.",
                    'current_model': model_stat['model']
                })
        
        # Budget projection warnings
        monthly_info = self.get_monthly_costs()
        if monthly_info['projected_monthly_cost'] > self.monthly_budget:
            recommendations.append({
                'type': 'budget_warning',
                'priority': 'high',
                'message': f"Projected monthly cost (${monthly_info['projected_monthly_cost']:.2f}) "
                         f"exceeds budget (${self.monthly_budget:.2f}). Consider cost optimization.",
                'projected_cost': monthly_info['projected_monthly_cost'],
                'budget': self.monthly_budget
            })
        
        return recommendations
    
    def export_cost_report(self, days: int = 30) -> str:
        """Export a detailed cost report."""
        stats = self.get_usage_stats(days)
        monthly_info = self.get_monthly_costs()
        recommendations = self.get_model_recommendations()
        
        report_lines = [
            f"# LLM Cost Report ({days} days)",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            "## Summary",
            f"- Total Cost: ${stats['total_cost']:.4f}",
            f"- Total Requests: {stats['total_requests']:,}",
            f"- Success Rate: {stats['success_rate']:.1%}",
            f"- Avg Cost/Request: ${stats['avg_cost_per_request']:.6f}",
            f"- Total Tokens: {stats['total_tokens']:,}",
            "",
            "## Current Month",
            f"- Month Cost: ${monthly_info['current_month_cost']:.4f}",
            f"- Budget: ${monthly_info['monthly_budget']:.2f}",
            f"- Budget Used: {monthly_info['budget_usage_percent']:.1%}",
            f"- Projected: ${monthly_info['projected_monthly_cost']:.2f}",
            "",
            "## Model Breakdown",
        ]
        
        for model in stats['model_breakdown']:
            report_lines.append(
                f"- {model['model']} ({model['provider']}): "
                f"${model['cost']:.4f} | {model['requests']} requests | "
                f"{model['tokens']:,} tokens"
            )
        
        if recommendations:
            report_lines.extend([
                "",
                "## Recommendations",
            ])
            for rec in recommendations:
                report_lines.append(f"- {rec['message']}")
        
        return "\n".join(report_lines)