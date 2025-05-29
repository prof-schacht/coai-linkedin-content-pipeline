#!/usr/bin/env python3
"""
Test script for LiteLLM connection.
Verifies Ollama connectivity and fallback to cloud models.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.litellm_config import get_litellm_config
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_connection():
    """Test basic connection to default model."""
    print("\n=== Testing Basic Connection ===")
    config = get_litellm_config()
    
    print(f"Ollama Host: {config.ollama_host}")
    print(f"Default Model: {config.default_model}")
    
    # Test connection
    if config.test_connection():
        print("✅ Connection test passed!")
        return True
    else:
        print("❌ Connection test failed!")
        return False


def test_model_listing():
    """Test listing available models."""
    print("\n=== Testing Model Listing ===")
    config = get_litellm_config()
    
    available_models = config.list_models()
    print(f"Available models ({len(available_models)}):")
    for model in available_models:
        print(f"  - {model}")
    
    return len(available_models) > 0


def test_simple_completion():
    """Test a simple completion request."""
    print("\n=== Testing Simple Completion ===")
    config = get_litellm_config()
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Say 'Hello, COAI!' in exactly 3 words."}
    ]
    
    try:
        start_time = time.time()
        response = config.complete(messages, max_tokens=20)
        elapsed = time.time() - start_time
        
        content = response.choices[0].message.content
        print(f"Response: {content}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Model used: {response.model}")
        
        return True
    except Exception as e:
        print(f"❌ Completion failed: {e}")
        return False


def test_model_fallback():
    """Test model fallback functionality."""
    print("\n=== Testing Model Fallback ===")
    config = get_litellm_config()
    
    # Try with a non-existent model first
    messages = [{"role": "user", "content": "Test fallback"}]
    
    try:
        # Override model priority to test fallback
        original_priority = config.model_priority
        config.model_priority = ["ollama/non-existent-model", config.default_model]
        
        response = config.complete(messages, max_tokens=10)
        print(f"✅ Fallback successful! Used model: {response.model}")
        
        # Restore original priority
        config.model_priority = original_priority
        return True
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
        return False


def test_response_timing():
    """Test and measure response times for cost tracking."""
    print("\n=== Testing Response Times ===")
    config = get_litellm_config()
    
    test_prompts = [
        "What is 2+2?",
        "Write a haiku about AI safety.",
        "Explain mechanistic interpretability in one sentence."
    ]
    
    total_time = 0
    for i, prompt in enumerate(test_prompts, 1):
        messages = [{"role": "user", "content": prompt}]
        
        try:
            start_time = time.time()
            response = config.complete(messages, max_tokens=50)
            elapsed = time.time() - start_time
            total_time += elapsed
            
            print(f"Test {i}: {elapsed:.2f}s - {prompt[:30]}...")
        except Exception as e:
            print(f"Test {i} failed: {e}")
    
    if total_time > 0:
        avg_time = total_time / len(test_prompts)
        print(f"\nAverage response time: {avg_time:.2f}s")
        print(f"Total cost: ${config.total_cost:.4f}")
    
    return True


def main():
    """Run all tests."""
    print("🚀 LiteLLM Connection Test Suite")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Run tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Model Listing", test_model_listing),
        ("Simple Completion", test_simple_completion),
        ("Model Fallback", test_model_fallback),
        ("Response Timing", test_response_timing),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())