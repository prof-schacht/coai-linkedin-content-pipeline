"""
LiteLLM configuration for flexible LLM usage.
Supports switching between local (Ollama) and cloud LLMs.
"""

import os
from typing import Dict, List, Optional, Any
import litellm
from litellm import completion
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LiteLLMConfig:
    """Configuration and routing for LiteLLM with Ollama and cloud providers."""
    
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.default_model = os.getenv("DEFAULT_MODEL", "ollama/deepseek-r1:1.5b")
        self.model_priority = os.getenv("MODEL_PRIORITY", "ollama/deepseek-r1:1.5b,ollama/qwen3:8b,gpt-3.5-turbo,claude-3-sonnet").split(",")
        
        # Set verbose mode for debugging
        litellm.set_verbose = os.getenv("LITELLM_VERBOSE", "False").lower() == "true"
        
        # Configure Ollama base URL
        os.environ["OLLAMA_API_BASE"] = self.ollama_host
        
        # Track costs
        self.total_cost = 0.0
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET_USD", "100"))
        self.cost_alert_threshold = float(os.getenv("COST_ALERT_THRESHOLD", "0.8"))
        
        logger.info(f"LiteLLM configured with Ollama host: {self.ollama_host}")
        logger.info(f"Default model: {self.default_model}")
        logger.info(f"Model priority: {self.model_priority}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from all configured providers."""
        available = []
        
        # Check Ollama models
        try:
            import requests
            response = requests.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    available.append(f"ollama/{model['name']}")
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
        
        # Check for cloud provider API keys
        if os.getenv("OPENAI_API_KEY"):
            available.extend(["gpt-3.5-turbo", "gpt-4"])
        
        if os.getenv("ANTHROPIC_API_KEY"):
            available.extend(["claude-3-sonnet-20240229", "claude-3-opus-20240229"])
        
        if os.getenv("GOOGLE_API_KEY"):
            available.extend(["gemini-pro"])
        
        return available
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete a chat conversation with automatic model fallback.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Specific model to use (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments passed to litellm.completion
            
        Returns:
            Response dictionary from litellm
        """
        models_to_try = [model] if model else self.model_priority
        available_models = self.get_available_models()
        
        last_error = None
        for model_name in models_to_try:
            if model_name not in available_models:
                logger.debug(f"Model {model_name} not available, skipping")
                continue
                
            try:
                logger.info(f"Attempting completion with model: {model_name}")
                
                response = completion(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Track costs
                if hasattr(response, 'usage'):
                    cost = self._calculate_cost(model_name, response.usage)
                    self.total_cost += cost
                    logger.info(f"Request cost: ${cost:.4f}, Total: ${self.total_cost:.2f}")
                    
                    if self.total_cost > self.monthly_budget * self.cost_alert_threshold:
                        logger.warning(f"Cost alert: ${self.total_cost:.2f} exceeds {self.cost_alert_threshold*100}% of budget")
                
                return response
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                last_error = e
                continue
        
        # If all models failed, raise the last error
        if last_error:
            raise last_error
        else:
            raise ValueError("No models available for completion")
    
    def _calculate_cost(self, model: str, usage: Dict) -> float:
        """Calculate cost based on model and token usage."""
        # Simplified cost calculation - in production, use actual pricing
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.03,
            "claude-3-sonnet": 0.003,
            "claude-3-opus": 0.015,
            "gemini-pro": 0.001,
        }
        
        # Ollama models are free
        if model.startswith("ollama/"):
            return 0.0
        
        # Default cost if model not in list
        rate = cost_per_1k_tokens.get(model, 0.001)
        total_tokens = usage.get("total_tokens", 0)
        
        return (total_tokens / 1000) * rate
    
    def list_models(self) -> List[str]:
        """List all available models."""
        return self.get_available_models()
    
    def test_connection(self) -> bool:
        """Test connection to default model."""
        try:
            response = self.complete(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Singleton instance
_config = None


def get_litellm_config() -> LiteLLMConfig:
    """Get singleton LiteLLM configuration."""
    global _config
    if _config is None:
        _config = LiteLLMConfig()
    return _config