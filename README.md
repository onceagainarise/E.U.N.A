# E.U.N.A. (Evolvable Unified Neural Agent)

🤖 **E.U.N.A.** is an advanced multi-agent orchestration system that can solve diverse tasks by coordinating existing agents or dynamically generating new task-specific agents on the fly.

## 🌟 Features

- **Dynamic Agent Generation**: Creates new agents with code generation and validation
- **Multi-Agent Orchestration**: Coordinates specialized agents for complex tasks
- **Safety & Governance**: Built-in safety constraints, rate limiting, and PII protection
- **Tool Management**: Whitelisted tool system with manifest-based governance
- **Multiple Interfaces**: CLI, Web (with voice input), and API interfaces
- **Memory System**: Short-term context and long-term agent registry
- **Intent Classification**: Intelligent routing to appropriate agents

## 🏗️ Architecture

```
User ⇄ Interface (CLI/Web/Voice)
        ⇓
   Controller (LLM)
     ├─ Intent Router
     ├─ Planner
     ├─ Tool/Agent Selector
     ├─ Agent Generator (LLM)
     └─ Validator + Registry Manager
            ├─ Agent Registry (metadata, code)
            └─ Memory Store (RAG, vectors, prefs)
```

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd E.U.N.A
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running E.U.N.A.

#### CLI Mode (Default)
```bash
python main.py
```

#### Web Interface (with Voice Input)
```bash
python main.py --web
```
Then open http://localhost:8000 in your browser.

**Voice Input Features:**
- 🎤 Click the microphone button to start voice input
- 🔴 Red indicator shows when listening
- ⌨️ Press `Ctrl+M` (or `Cmd+M` on Mac) to toggle voice input
- 🛑 Press `Escape` to stop listening
- 🔊 Supports real-time speech-to-text conversion
- 🌐 Works in modern browsers (Chrome, Edge, Safari)

#### System Tests
```bash
python main.py --test
```

#### Custom Port
```bash
python main.py --web --port 3000
```

## 💬 Usage Examples

### CLI Examples
```bash
# Interactive mode
python main.py

# Single request
python main.py -r "Find a hotel in Mumbai under ₹5000"

# System status
python main.py --status
```

### API Examples
```python
from euna import EUNA

# Initialize system
euna = EUNA()

# Process request
result = euna.process_request(
    "Find a quiet beachside hotel in Goa under ₹10,000",
    constraints={"budget": 10000, "nights": 2}
)

print(f"Agent: {result.agent_used}")
print(f"Summary: {result.result_summary}")
```

## 🔧 Core Components

### 1. BaseAgent Interface
All agents inherit from `BaseAgent` and implement:
- `name()`: Agent identifier
- `capabilities()`: List of capabilities
- `input_schema()`: Expected input format
- `output_schema()`: Output format
- `handle()`: Main execution logic

### 2. Controller
- Analyzes user intent
- Plans execution steps
- Selects appropriate agents
- Coordinates multi-step workflows

### 3. Agent Generator
- Generates Python agent code from specifications
- Validates code for safety compliance
- Registers new agents in the system

### 4. Memory Store
- **Short-term**: Conversation context, task state
- **Long-term**: Agent registry, tool manifests, user preferences

### 5. Safety Manager
- Rate limiting and permission gating
- PII detection and redaction
- Tool whitelisting and validation
- Security policy enforcement

### 6. Tool Manager
- Loads and validates tool manifests
- Provides safe tool execution
- Manages tool permissions and constraints

## 🛡️ Safety Features

- **Code Validation**: Static analysis of generated agents
- **Tool Whitelisting**: Only approved tools can be used
- **Rate Limiting**: Prevents abuse and overuse
- **PII Protection**: Automatic detection and redaction
- **Permission Gating**: User-based access controls
- **Audit Logging**: Complete activity tracking

## 📁 Project Structure

```
E.U.N.A/
├── main.py                 # Main entry point
├── euna.py                 # Core E.U.N.A. interface
├── controller.py           # Request orchestration
├── agent_generator.py      # Dynamic agent creation
├── base_agent.py          # Agent interface
├── memory_store.py        # Memory management
├── tool_manifest.py       # Tool management
├── safety.py              # Safety & governance
├── schemas.py             # Data schemas
├── cli.py                 # CLI interface
├── web_app.py             # Web interface
├── templates/             # Web templates
│   └── index.html
├── data/                  # Persistent data
│   ├── agent_registry.json
│   ├── conversation_context.json
│   └── user_preferences.json
├── generated_agents/      # Generated agent modules
├── tools/                 # Tool implementations
│   └── manifest.json
└── requirements.txt       # Dependencies
```

## 🎯 Example Use Cases

### Travel Planning
```
"Find a quiet beachside hotel in Goa under ₹10,000 with ocean view"
→ Generates TravelAgent with hotel search, price filtering, view validation
```

### Research Tasks
```
"Research the latest trends in AI agent architectures"
→ Uses ResearchAgent with web search, data analysis, summarization
```

### DIY Projects
```
"Help me build a wooden bookshelf for my living room"
→ Creates DIYAgent with material calculation, step planning, tool requirements
```

## 🔌 API Reference

### Main Interface
```python
class EUNA:
    def process_request(user_input, user_id, context, constraints) -> TaskResult
    def list_available_agents() -> Dict
    def get_agent_details(agent_name) -> Dict
    def list_available_tools() -> Dict
    def get_system_status() -> Dict
```

### Web API Endpoints
- `POST /api/chat` - Process chat message
- `GET /api/status` - System status
- `GET /api/agents` - List agents
- `GET /api/tools` - List tools
- `GET /api/agents/{name}` - Agent details
- `POST /api/clear-context` - Clear context

## ⚙️ Configuration

### Safety Configuration
```python
config = {
    "safety": {
        "max_requests_per_minute": 60,
        "max_tool_calls_per_minute": 30,
        "pii_redaction_enabled": True,
        "rate_limiting_enabled": True
    }
}
```

### Tool Manifest Example
```json
{
  "tools": {
    "hotel_api": {
      "fn": "search_hotels",
      "args_schema": {"location": "str", "max_price": "int"},
      "returns": {"hotels": "list"},
      "safety": {"rate_limit_per_min": 5}
    }
  }
}
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python main.py --test
```

Tests include:
- System initialization
- Request processing
- Agent generation
- Tool execution
- Safety validation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Run system tests
3. Check logs in the `data/` directory
4. Open an issue on GitHub

---

**E.U.N.A.** - Evolving intelligence through collaborative agents 🚀
