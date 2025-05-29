# COAI LinkedIn Content Pipeline

An AI-powered content generation system that creates engaging LinkedIn posts about AI safety, control, and mechanistic interpretability by combining insights from X.com discussions and arXiv papers.

## 🎯 Project Goals

- Monitor X.com for discussions on technical AI governance, AI control, AI safety, and mechanistic interpretability
- Fetch and analyze relevant papers from arXiv (cs.AI, cs.CL categories)
- Generate authentic, engaging LinkedIn posts that don't sound artificial
- Identify potential podcast interviewees from LinkedIn network
- Increase visibility of COAI Research in the AI safety community

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LiteLLM Router                           │
│  (Switches between Ollama, OpenAI, Claude, Gemini, etc.)   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────┬───────────┴───────────┬──────────────────┐
│  Data Collector │   Content Pipeline    │  LinkedIn Intel  │
│  - X.com Scanner│   - CrewAI Agents    │  - Network Map   │
│  - arXiv Fetcher│   - Post Generator   │  - Expert Finder │
└─────────────────┴───────────────────────┴──────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/prof-schacht/coai-linkedin-content-pipeline.git
cd coai-linkedin-content-pipeline

# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run setup
python scripts/setup_database.py

# Start Ollama (for local LLMs)
docker-compose up -d ollama

# Run the pipeline
python scripts/daily_run.py
```

## 📁 Project Structure

```
coai-linkedin-content-pipeline/
├── docker-compose.yml          # Services configuration
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── config/
│   ├── litellm_config.py      # LLM routing configuration
│   ├── agents_config.py       # CrewAI agents setup
│   └── topics_config.py       # AI safety topics configuration
├── src/
│   ├── collectors/
│   │   ├── arxiv_monitor.py   # arXiv paper fetcher (cs.AI, cs.CL)
│   │   └── x_scanner.py       # X.com content scanner
│   ├── agents/
│   │   ├── base_agent.py      # Base agent class
│   │   ├── research_analyst.py # Analyzes papers and discussions
│   │   ├── content_strategist.py # Plans post structure
│   │   ├── linkedin_writer.py  # Generates authentic posts
│   │   └── interview_scout.py  # Identifies podcast candidates
│   ├── generators/
│   │   ├── post_creator.py    # Assembles final posts
│   │   └── authenticity_engine.py # Ensures natural tone
│   ├── analyzers/
│   │   ├── network_mapper.py  # LinkedIn connection analysis
│   │   └── expert_scorer.py   # Ranks potential interviewees
│   └── utils/
│       ├── litellm_router.py  # LLM switching logic
│       └── cache_manager.py   # Response caching
├── scripts/
│   ├── setup_database.py      # Initial database setup
│   ├── import_connections.py  # LinkedIn network import
│   └── daily_run.py          # Main execution script
└── tests/
    └── ...                    # Test files
```

## 🔧 Key Features

### LiteLLM Integration
- Seamless switching between local (Ollama) and cloud LLMs
- Cost optimization with intelligent routing
- Fallback chains for reliability

### Data Collection
- **arXiv Monitor**: Daily checks of cs.AI and cs.CL categories
- **X.com Scanner**: Tracks discussions on AI safety topics
- **Cross-referencing**: Links papers mentioned in X.com posts

### CrewAI Agents
1. **Research Analyst**: Extracts insights from papers and discussions
2. **Content Strategist**: Plans engaging post structures
3. **LinkedIn Writer**: Creates authentic, non-robotic content
4. **Interview Scout**: Identifies experts in your network for podcasts

### Authenticity Features
- Personal writing style analysis
- Natural language variations
- Engagement elements (questions, observations)
- Smart mention suggestions

## 📊 Topics Monitored

- Technical AI Governance
- AI Control
- AI Safety
- Mechanistic Interpretability

## 🎯 Use Cases

1. **Daily Content Generation**: Automated creation of 1-2 LinkedIn posts
2. **Expert Discovery**: Find potential podcast guests in your network
3. **Trend Analysis**: Identify emerging topics in AI safety
4. **Network Growth**: Connect with relevant professionals

## 🔒 Security & Privacy

- API keys stored in environment variables
- No storage of private LinkedIn data
- Respects rate limits and ToS
- Local LLM option for sensitive content

## 📈 Success Metrics

- Post engagement rate
- Network growth
- Interview candidates identified
- COAI Research visibility

## 🤝 Contributing

See issues for current tasks. We follow a simple PR workflow:
1. Pick an issue
2. Create a feature branch
3. Submit PR with tests
4. Code review and merge

## 📝 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

- Built for [COAI Research](https://coairesearch.org)
- Powered by CrewAI, LiteLLM, and arXiv
