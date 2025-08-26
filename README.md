# EUNA MVP - Evolvable Unified Neural Agent

A complete MVP implementation of EUNA (Evolvable Unified Neural Agent) - an agentic AI orchestration system that dynamically creates and manages specialized AI agents to perform complex multi-step tasks autonomously.

## 🚀 Key Features

### Dynamic Agent Generation
- **On-Demand Agent Creation**: EUNA analyzes incoming tasks and creates specialized agents tailored to specific requirements
- **Default Agents**: Pre-built specialists (SummarizerAgent, SearchAgent, CodingAgent, SchedulerAgent)
- **Dynamic Agents**: AI-generated agents with custom capabilities using GROQ LLM reasoning

### Intelligent Task Orchestration
- **Master Orchestrator**: Coordinates multiple agents for complex workflows
- **Task Analysis**: Uses GROQ LLM to determine optimal agent combinations
- **Progress Tracking**: Real-time monitoring of task execution and agent status

### Comprehensive Tool Integration
- **Web Search**: DuckDuckGo integration for information gathering
- **Calculations**: Mathematical operations and computations
- **Text Processing**: Summarization and content analysis
- **File Operations**: Reading and processing various file formats
- **API Integration**: HTTP requests and external service calls

### Memory & Context Management
- **Semantic Memory**: Pinecone vector database for contextual information storage
- **Session Management**: User preference and context tracking
- **Learning**: System improves from previous task executions

### Modern Web Interface
- **Streamlit Frontend**: Clean, interactive web interface
- **Real-time Updates**: WebSocket integration for live task monitoring
- **Analytics Dashboard**: System performance and usage statistics

## 🏗️ Architecture

```
euna_mvp/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                     # FastAPI main application
├── frontend/
│   └── streamlit_app.py        # Streamlit UI
├── core/
│   ├── orchestrator.py         # Master orchestration logic
│   ├── agent_factory.py        # Agent creation and management
│   └── task_manager.py         # Task coordination
├── agents/
│   ├── base_agent.py          # Abstract base agent class
│   ├── default_agents.py      # Predefined agents
│   └── dynamic_agent.py       # Dynamically generated agents
├── services/
│   ├── groq_service.py        # GROQ LLM integration
│   ├── memory_service.py      # Pinecone vector store
│   └── database_service.py    # SQLite operations
├── tools/
│   ├── tool_registry.py       # Tool registration system
│   ├── default_tools.py       # Basic tools
│   └── tool_executor.py       # Tool execution engine
├── database/
│   └── models.py              # SQLAlchemy models
└── config/
    └── settings.py            # Configuration management
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- GROQ API key
- Pinecone API key (optional, fallback memory available)

### 1. Clone and Install Dependencies
```bash
git clone <repository-url>
cd euna_mvp
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` file with your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment_here
```

### 3. Database Setup
The SQLite database will be created automatically on first run.

### 4. Start the Backend API
```bash
python main.py
```
API will be available at `http://localhost:8000`

### 5. Start the Frontend
```bash
streamlit run frontend/streamlit_app.py
```
Web interface will be available at `http://localhost:8501`

## 🎯 Demo Scenarios

### 1. Trip Planning
**Input**: "Plan a 3-day trip to Tokyo with a budget of $2000, focusing on cultural experiences and local food"

**EUNA Response**:
- Creates `TravelPlannerAgent` and `BudgetManagerAgent`
- Uses web search to find attractions and restaurants
- Generates comprehensive itinerary with budget breakdown

### 2. Document Analysis
**Input**: "Summarize this 20-page report and extract key action items"

**EUNA Response**:
- Creates `SummarizerAgent` and `AnalysisAgent`
- Processes document content
- Provides structured summary with actionable insights

### 3. Code Development
**Input**: "Create a Python Flask API for user authentication with JWT"

**EUNA Response**:
- Creates `CodingAgent` and `SecurityAgent`
- Generates complete code with best practices
- Includes documentation and usage examples

### 4. Research Task
**Input**: "Research the latest trends in renewable energy and create a presentation outline"

**EUNA Response**:
- Creates `SearchAgent` and `ContentAgent`
- Gathers information from multiple sources
- Structures findings into presentation format

## 📚 API Documentation

### Core Endpoints

#### Submit Task
```http
POST /api/v1/tasks/submit
Content-Type: application/json

{
  "user_input": "Your task description",
  "priority": "medium",
  "session_id": "optional_session_id"
}
```

#### Get Task Status
```http
GET /api/v1/tasks/{task_id}
```

#### List Active Agents
```http
GET /api/v1/agents/active
```

#### Create Custom Agent
```http
POST /api/v1/agents/create
Content-Type: application/json

{
  "task_id": 1,
  "agent_type": "CustomAgent",
  "role": "Specialized role description"
}
```

#### WebSocket Updates
```
WS /ws/task-updates
```

### Response Formats

#### Task Submission Response
```json
{
  "task_id": 123,
  "status": "submitted",
  "analysis": {
    "complexity": "moderate",
    "requires_dynamic_agents": true,
    "suggested_agents": [...],
    "estimated_duration": "3-5 minutes"
  }
}
```

#### Task Status Response
```json
{
  "task_id": 123,
  "status": "completed",
  "user_input": "Original task description",
  "final_result": {
    "final_answer": "Comprehensive response",
    "key_insights": ["insight1", "insight2"],
    "confidence_score": 0.95
  },
  "agents": [...],
  "logs": [...]
}
```

## 🔧 Configuration

### Environment Variables
- `GROQ_API_KEY`: Required for LLM reasoning
- `PINECONE_API_KEY`: Optional for semantic memory
- `DATABASE_URL`: SQLite database path
- `DEBUG`: Enable debug mode
- `LOG_LEVEL`: Logging verbosity
- `MAX_AGENTS`: Maximum concurrent agents
- `TASK_TIMEOUT`: Task execution timeout

### Agent Types
- **SummarizerAgent**: Text summarization and analysis
- **SearchAgent**: Web search and information gathering
- **CodingAgent**: Code generation and review
- **SchedulerAgent**: Task scheduling and time management
- **DynamicAgent**: Custom agents generated on-demand

### Available Tools
- **web_search**: DuckDuckGo web search
- **calculator**: Mathematical computations
- **text_summarizer**: Text analysis and summarization
- **file_reader**: File content reading
- **json_parser**: JSON data processing
- **http_request**: API calls and web requests
- **datetime_tool**: Date and time operations

## 🎮 Usage Examples

### Basic Task Submission (Python)
```python
import requests

response = requests.post("http://localhost:8000/api/v1/tasks/submit", json={
    "user_input": "Calculate compound interest on $10000 at 7% for 10 years",
    "priority": "medium"
})

task_id = response.json()["task_id"]
print(f"Task submitted: {task_id}")
```

### Monitor Task Progress
```python
import time
import requests

task_id = 123
while True:
    status = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}").json()
    print(f"Status: {status['status']}")
    
    if status["status"] in ["completed", "failed"]:
        print("Final result:", status.get("final_result"))
        break
    
    time.sleep(5)
```

## 🚦 System Monitoring

### Health Check
```http
GET /health
```

### System Statistics
```http
GET /api/v1/stats
```

### Memory Search
```http
GET /api/v1/memory/search?query=your_search_terms
```

## 🔍 Troubleshooting

### Common Issues

1. **GROQ API Errors**
   - Verify API key is correct
   - Check rate limits
   - Ensure network connectivity

2. **Database Issues**
   - Check file permissions
   - Verify SQLite installation
   - Clear database file if corrupted

3. **Memory Service Issues**
   - Pinecone API key validation
   - Fallback to in-memory storage
   - Check vector dimensions

4. **Tool Execution Failures**
   - Network connectivity for web tools
   - Parameter validation
   - Tool-specific requirements

### Debugging

Enable debug mode:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f euna_mvp.log
```

## 🔮 Future Enhancements

### Planned Features
- **Multi-modal Agents**: Image and video processing capabilities
- **Advanced Memory**: Long-term learning and pattern recognition
- **Agent Marketplace**: Community-contributed agent templates
- **Workflow Designer**: Visual workflow creation interface
- **Performance Optimization**: Caching and parallel execution
- **Security Enhancements**: Authentication and authorization
- **Cloud Deployment**: Docker containers and cloud integration

### Extensibility
- **Custom Tools**: Easy integration of new tools
- **Agent Templates**: Reusable agent configurations
- **Plugin System**: Third-party extensions
- **API Integrations**: Connect to external services

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request



**EUNA MVP** - Demonstrating the future of AI agent orchestration through dynamic, specialized agent creation and intelligent task coordination.
