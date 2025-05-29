"""
Pytest configuration and fixtures for test suite.
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    test_env = {
        "TESTING": "True",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_coai",
        "REDIS_URL": "redis://localhost:6379/1",  # Use different DB for tests
        "OLLAMA_HOST": "http://localhost:11434",
        "LITELLM_VERBOSE": "False"
    }
    
    # Save original environment
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_ollama_response():
    """Provide a mock Ollama API response."""
    return {
        "models": [
            {"name": "deepseek-r1:1.5b", "size": "1.5B"},
            {"name": "qwen3:8b", "size": "8B"},
            {"name": "llama2:7b", "size": "7B"}
        ]
    }