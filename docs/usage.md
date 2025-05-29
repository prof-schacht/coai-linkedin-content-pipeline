# COAI LinkedIn Content Pipeline - Usage Guide

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis
- Ollama (for local LLM)
- Docker & Docker Compose (optional, for containerized deployment)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/prof-schacht/coai-linkedin-content-pipeline.git
   cd coai-linkedin-content-pipeline
   ```

2. **Set up Python environment with uv:**
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Initialize project and create virtual environment
   uv init --python 3.11
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   uv pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Verify services are running:**
   ```bash
   # Check PostgreSQL
   pg_isready -h localhost -p 5432

   # Check Redis
   redis-cli ping

   # Check Ollama
   curl http://localhost:11434/api/tags
   ```

### Testing the Setup

Run the LiteLLM connection test to verify everything is working:

```bash
python scripts/test_litellm_connection.py
```

This will test:
- ✅ Basic connection to Ollama
- ✅ Model listing
- ✅ Simple completion
- ✅ Model fallback
- ✅ Response timing

### Running Tests

Run the full test suite with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=config

# Run specific test file
pytest tests/test_litellm_config.py -v
```

## 📦 Project Structure

```
coai-linkedin-content-pipeline/
├── config/               # Configuration modules
│   ├── __init__.py
│   └── litellm_config.py # LiteLLM routing configuration
├── src/                  # Source code
│   ├── collectors/       # Data collection modules
│   ├── agents/          # CrewAI agents
│   ├── generators/      # Content generation
│   ├── analyzers/       # Analysis tools
│   └── utils/           # Utility functions
├── scripts/             # Executable scripts
│   └── test_litellm_connection.py
├── tests/               # Test suite
│   ├── conftest.py
│   └── test_litellm_config.py
├── docs/                # Documentation
│   └── usage.md         # This file
└── tmp/                 # Development notes
    ├── scratchpad.md
    └── test_advice.md
```

## 🔧 Configuration

### LiteLLM Configuration

The system uses LiteLLM for flexible LLM routing. Key features:

1. **Primary Model**: Ollama with deepseek-r1:1.5b (local, free)
2. **Fallback Models**: Cloud providers (OpenAI, Anthropic, Google)
3. **Automatic Failover**: If one model fails, tries the next
4. **Cost Tracking**: Monitors usage and alerts on budget threshold

### Environment Variables

Key environment variables in `.env`:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=ollama/deepseek-r1:1.5b

# Model Priority (comma-separated)
MODEL_PRIORITY=ollama/deepseek-r1:1.5b,ollama/qwen3:8b,gpt-3.5-turbo

# Optional Cloud Providers
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Cost Management
MONTHLY_BUDGET_USD=100
COST_ALERT_THRESHOLD=0.8

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/coai_pipeline
REDIS_URL=redis://localhost:6379/0
```

## 🐳 Docker Deployment

For production deployment, use Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services included:
- PostgreSQL database
- Redis cache
- Ollama LLM server
- Celery workers
- Flower monitoring (optional)
- pgAdmin (optional, development only)

## 🔍 Monitoring

### Cost Tracking

The system automatically tracks LLM usage costs:
- Free for Ollama models
- Tracks token usage for cloud models
- Alerts when approaching budget threshold

### Logging

Logs are configured at INFO level by default. To enable debug logging:

```bash
export LITELLM_VERBOSE=True
export LOG_LEVEL=DEBUG
```

## 🛠️ Development

### Adding New Features

1. Create feature branch
2. Implement with tests
3. Update documentation
4. Create pull request

### Code Style

- Use `black` for formatting
- Follow PEP 8 guidelines
- Write comprehensive docstrings
- Add type hints where applicable

### Testing Guidelines

- Write pytest tests for all new functions
- Aim for >80% code coverage
- Use mocks for external dependencies
- Include both unit and integration tests

## 📚 Next Steps

After setup is complete, proceed to implement:
1. ✅ arXiv paper collector (Issue #2) - COMPLETED
2. X.com web scraper (Issue #3)
3. CrewAI agents (Issue #4)
4. LinkedIn network analyzer (Issue #5)
5. Content pipeline (Issue #6)
6. Monitoring system (Issue #7)

## 🔬 arXiv Paper Collection

The arXiv paper collector monitors cs.AI and cs.CL categories for papers related to AI safety, control, and interpretability.

### Features

- **Automatic Collection**: Fetches papers from specified categories daily
- **Relevance Scoring**: Calculates relevance based on keywords and authors
- **LLM Summarization**: Generates concise summaries for relevant papers
- **Cross-referencing**: Extracts arXiv paper mentions from text
- **Database Storage**: Stores papers with metadata and search indexes

### Running the Collector

```bash
# Basic collection (uses default settings)
python scripts/fetch_arxiv_papers.py

# Dry run - see what would be collected
python scripts/fetch_arxiv_papers.py --dry-run

# Collect papers from specific date
python scripts/fetch_arxiv_papers.py --date 2024-01-01

# Collect papers from last N days
python scripts/fetch_arxiv_papers.py --days 14

# Show database statistics only
python scripts/fetch_arxiv_papers.py --stats-only
```

### Setting Up Daily Collection

```bash
# Run the cron setup script
./scripts/cron_setup.sh

# Or manually add to crontab:
# Daily at 2 AM UTC
0 2 * * * cd /path/to/project && source .venv/bin/activate && python scripts/fetch_arxiv_papers.py
```

### Testing

```bash
# Run arXiv collector tests
pytest tests/test_arxiv_monitor.py -v

# Run with coverage
pytest tests/test_arxiv_monitor.py --cov=src.collectors.arxiv_monitor
```

### Database Management

```bash
# Run migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Description"

# View papers in database
psql -U codeuser -d coai_pipeline -c "SELECT arxiv_id, title, relevance_score FROM papers ORDER BY submission_date DESC LIMIT 10;"
```

## 🤝 Support

For issues or questions:
- Check the [GitHub Issues](https://github.com/prof-schacht/coai-linkedin-content-pipeline/issues)
- Review test output in `tmp/test_advice.md`
- Check development notes in `tmp/scratchpad.md`