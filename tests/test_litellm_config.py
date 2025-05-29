"""
Pytest tests for LiteLLM configuration module.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, Mock

from config.litellm_config import LiteLLMConfig, get_litellm_config


class TestLiteLLMConfig:
    """Test cases for LiteLLMConfig class."""
    
    @pytest.fixture
    def config(self):
        """Create a fresh config instance for each test."""
        # Reset singleton
        import config.litellm_config
        config.litellm_config._config = None
        
        with patch.dict(os.environ, {
            "OLLAMA_HOST": "http://test-ollama:11434",
            "DEFAULT_MODEL": "ollama/test-model",
            "MODEL_PRIORITY": "ollama/test1,ollama/test2,gpt-3.5-turbo",
            "MONTHLY_BUDGET_USD": "50",
            "COST_ALERT_THRESHOLD": "0.8"
        }):
            yield LiteLLMConfig()
    
    def test_initialization(self, config):
        """Test config initialization with environment variables."""
        assert config.ollama_host == "http://test-ollama:11434"
        assert config.default_model == "ollama/test-model"
        assert config.model_priority == ["ollama/test1", "ollama/test2", "gpt-3.5-turbo"]
        assert config.monthly_budget == 50.0
        assert config.cost_alert_threshold == 0.8
        assert os.environ["OLLAMA_API_BASE"] == "http://test-ollama:11434"
    
    def test_get_available_models_ollama_only(self, config):
        """Test getting available models from Ollama only."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "deepseek-r1:1.5b"},
                {"name": "qwen3:8b"}
            ]
        }
        
        with patch("requests.get", return_value=mock_response):
            models = config.get_available_models()
        
        assert "ollama/deepseek-r1:1.5b" in models
        assert "ollama/qwen3:8b" in models
        assert len(models) == 2
    
    def test_get_available_models_with_cloud_providers(self, config):
        """Test getting available models including cloud providers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "test-model"}]}
        
        with patch("requests.get", return_value=mock_response):
            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "test-key",
                "ANTHROPIC_API_KEY": "test-key",
                "GOOGLE_API_KEY": "test-key"
            }):
                models = config.get_available_models()
        
        assert "ollama/test-model" in models
        assert "gpt-3.5-turbo" in models
        assert "claude-3-sonnet-20240229" in models
        assert "gemini-pro" in models
    
    def test_complete_successful(self, config):
        """Test successful completion with mocked response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello, world!"))]
        mock_response.usage = {"total_tokens": 10}
        mock_response.model = "ollama/test-model"
        
        with patch("litellm.completion", return_value=mock_response):
            with patch.object(config, "get_available_models", return_value=["ollama/test-model"]):
                response = config.complete([{"role": "user", "content": "Hello"}])
        
        assert response.choices[0].message.content == "Hello, world!"
        assert config.total_cost == 0.0  # Ollama models are free
    
    def test_complete_with_fallback(self, config):
        """Test completion with model fallback."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Fallback response"))]
        mock_response.usage = {"total_tokens": 20}
        mock_response.model = "gpt-3.5-turbo"
        
        def side_effect(model, **kwargs):
            if model == "ollama/test1":
                raise Exception("Model not available")
            return mock_response
        
        with patch("litellm.completion", side_effect=side_effect):
            with patch.object(config, "get_available_models", return_value=["ollama/test1", "gpt-3.5-turbo"]):
                config.model_priority = ["ollama/test1", "gpt-3.5-turbo"]
                response = config.complete([{"role": "user", "content": "Test"}])
        
        assert response.choices[0].message.content == "Fallback response"
        assert config.total_cost > 0  # Cloud model has cost
    
    def test_complete_all_models_fail(self, config):
        """Test completion when all models fail."""
        with patch("litellm.completion", side_effect=Exception("All models failed")):
            with patch.object(config, "get_available_models", return_value=["ollama/test-model"]):
                with pytest.raises(Exception, match="All models failed"):
                    config.complete([{"role": "user", "content": "Test"}])
    
    def test_calculate_cost_ollama(self, config):
        """Test cost calculation for Ollama models (should be free)."""
        usage = {"total_tokens": 1000}
        cost = config._calculate_cost("ollama/any-model", usage)
        assert cost == 0.0
    
    def test_calculate_cost_openai(self, config):
        """Test cost calculation for OpenAI models."""
        usage = {"total_tokens": 1000}
        cost = config._calculate_cost("gpt-3.5-turbo", usage)
        assert cost == 0.002  # 1000 tokens * $0.002/1k
    
    def test_calculate_cost_unknown_model(self, config):
        """Test cost calculation for unknown models."""
        usage = {"total_tokens": 1000}
        cost = config._calculate_cost("unknown-model", usage)
        assert cost == 0.001  # Default rate
    
    def test_cost_alert_threshold(self, config):
        """Test cost alert threshold warning."""
        config.total_cost = 45.0  # 90% of $50 budget
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = {"total_tokens": 1000}
        mock_response.model = "gpt-3.5-turbo"
        
        with patch("litellm.completion", return_value=mock_response):
            with patch.object(config, "get_available_models", return_value=["gpt-3.5-turbo"]):
                with patch("logging.Logger.warning") as mock_warning:
                    config.complete([{"role": "user", "content": "Test"}])
                    
                    # Check if warning was logged
                    mock_warning.assert_called()
                    warning_msg = mock_warning.call_args[0][0]
                    assert "Cost alert" in warning_msg
    
    def test_test_connection_success(self, config):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello"))]
        
        with patch.object(config, "complete", return_value=mock_response):
            assert config.test_connection() is True
    
    def test_test_connection_failure(self, config):
        """Test failed connection test."""
        with patch.object(config, "complete", side_effect=Exception("Connection failed")):
            assert config.test_connection() is False
    
    def test_singleton_pattern(self):
        """Test that get_litellm_config returns singleton instance."""
        config1 = get_litellm_config()
        config2 = get_litellm_config()
        assert config1 is config2


class TestIntegration:
    """Integration tests that require actual services."""
    
    @pytest.mark.skipif(
        not os.getenv("OLLAMA_HOST"),
        reason="Ollama not configured"
    )
    def test_real_ollama_connection(self):
        """Test real connection to Ollama if available."""
        config = get_litellm_config()
        
        # Only run if Ollama is actually available
        try:
            import requests
            response = requests.get(f"{config.ollama_host}/api/tags", timeout=2)
            if response.status_code != 200:
                pytest.skip("Ollama not available")
        except:
            pytest.skip("Ollama not available")
        
        # Test actual connection
        assert config.test_connection() is True