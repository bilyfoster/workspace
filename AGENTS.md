# Workspace v1.6.1 - Agent Documentation

## Overview
The Workspace is a multi-agent AI orchestration system running on macOS bare metal with Ollama local LLMs. It uses thread-based agents (not processes) for shared memory access.

**New in v1.5.0:**
- **Manager Agent** (🎩) - Primary point of contact and overseer
- **Dynamic Agent Creation** - Create new agents on-the-fly from templates or custom
- **Thinking Animations** - Visual indicators when agents are processing
- Full visibility into all agent activities

**Previous features:**
- Per-agent resource monitoring (CPU, memory)
- Individual agent management controls
- Better status icons and activity indicators

## Architecture

### Core Components
- **WorkspaceOrchestrator**: Central coordinator, singleton pattern
- **AgentRunner**: Thread-based agent execution with AgentSoul identity
- **MessageBus**: In-memory pub/sub for agent communication
- **MissionManager**: Task/mission CRUD with JSON persistence
- **OllamaClient**: Local LLM integration (qwen3.5:9b, dolphin3, gemma3)

### Agent Identity System
Each agent has a `soul.md` file defining:
- **name**: Display name
- **role**: Functional role (Strategist, Copywriter, etc.)
- **model**: Ollama model to use
- **essence**: Personality/core identity
- **skills**: List of capabilities

## Available Agents

### Core Team

| Agent | Role | Model | Key Skill |
|-------|------|-------|-----------|
| **Manager** | **Overseer** | **qwen3.5:9b** | **Team orchestration, primary contact** |
| Hunter | Lead Orchestrator | dolphin3 | Mission planning, delegation |
| Pepper | HR Manager | dolphin3 | Team coordination, wellness |
| Scout | Researcher | qwen3.5:9b | Information gathering |
| Sage | Analyst | qwen3.5:9b | Data analysis, insights |
| Shuri | Strategist | qwen3.5:9b | Strategic positioning |
| Quill | Copywriter | gemma3 | Creative writing |
| Wong | Engineer | qwen3-coder | Technical implementation |
| Code | Developer | qwen3-coder | Code generation |
| Pixel | Designer | gemma3 | Visual design |
| Guardian | Security Lead | qwen3.5:9b | Security analysis |
| Lingua | Translator | dolphin3 | Multi-language support |

### Dynamic Templates (v1.5.0)

| Template | Avatar | Skills |
|----------|--------|--------|
| Data Analyst | 📊 | Statistics, visualization, SQL |
| Legal Expert | ⚖️ | Contracts, compliance, research |
| Financial Analyst | 💰 | Modeling, investments, forecasting |
| Customer Support | 🎧 | Issue resolution, communication |
| DevOps Engineer | 🔧 | CI/CD, Docker, cloud |
| QA Tester | 🐞 | Test planning, bug reporting |
| UX Researcher | 🧪 | User studies, testing |
| Technical Writer | 📝 | Documentation, API guides |
| Sales Rep | 💼 | Lead gen, demos, CRM |
| Product Manager | 📱 | Roadmaps, prioritization |

## Dashboard Interface (v1.6.1)

### HUD Panel (Top - Collapsible)
```
┌─────────────────────────────────────────────────────────┐
│  🎯 Workspace    [Agents] [Working] [Alerts] ...   [▼]  │  ← ▲/▼ to collapse
├─────────────────────────────────────────────────────────┤
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐                          │
│  │🎩  │ │🎨  │ │💻  │                                  │  ← Click to chat
│  │Mgr │ │Pix │ │Code│                                  │
│  │IDLE│ │WORK│ │IDLE│                                  │
│  └────┘ └────┘ └────┘                                  │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- **Collapsible**: Click ▲/▼ to show/hide agent cards
- **Metrics**: Agents, Working, Alerts, Missions, Tasks
- **Agent Cards**: Click any to chat directly
- **Color-coded borders**: Green=Idle, Yellow=Working, Red=Error

### Main Chat Area
- Welcome message with hints
- Message history with user/agent bubbles
- Thinking animation (🧠 + bouncing dots)

### Sidebar Navigation
- 🏠 Dashboard (main chat)
- 🤖 Agent Control (spawn/manage agents)
- 📋 Missions (create/execute missions)
- 🚀 Spawn Manager
- 🧹 Clear Chat
2. **Chat** - 1-on-1 agent conversations (30s timeout)
3. **Group Chat** - Multi-agent discussions
4. **Spawn Agents** - Agent management (respawn/kill)
5. **Missions** - Task board with parallel execution
6. **Handoffs** - Manual/auto handoff management
7. **Alerts** - System notifications
8. **Analytics** - Activity tracking
9. **Logs** - Debug and error logs
10. **System** - Settings and configuration

## Key Features (v1.6.0)

### Parallel Task Execution
```python
orchestrator.execute_mission_parallel(mission_id)
# Runs all pending tasks concurrently with ThreadPoolExecutor
```

### HUD Dashboard (v1.6.1)
- **Collapsible panel** - Save space when needed
- **Real-time metrics** - Agent count, working, alerts, missions, tasks
- **Agent mini-cards** - Click to chat, color-coded by status
- **Working navigation** - All sidebar buttons functional

### Manager Overseer
- **Manager Agent** (🎩) as your primary point of contact
- Full visibility into all agent activities
- Natural language commands: "Who's working on what?"
- Manager can spawn agents and create new roles
- Live activity feed with thinking indicators

### Dynamic Agent Creation (NEW)
Create new agents on-the-fly:
```python
# From template
agent_factory.create_agent_from_template("data_analyst", "Atlas")

# Custom creation
agent_factory.create_custom_agent(
    name="Zeus",
    role="Cloud Architect",
    avatar="☁️",
    essence="Expert in cloud infrastructure...",
    skills=["AWS", "Terraform", "Kubernetes"]
)
```

### Visual Processing Indicators (NEW)
- 🧠 Thinking animation with bouncing dots
- Status badges with glow effects
- Real-time "working on..." indicators
- Brain pulse animation during processing

### Resource Monitoring
- Real-time CPU and memory tracking per agent
- System-wide resource summary
- Resource usage charts in Analytics
- Visual resource bars in Dashboard

### Mission Export
- Markdown format: `./exports/Mission_Name_YYYYMMDD_HHMMSS.md`
- JSON format available
- Includes all task results

### Auto-Handoff Detection
- Parses agent responses for handoff keywords
- Suggests next agent based on task type
- Beta feature, may need manual adjustment

## Usage Examples

### Chat with Manager (NEW)
The Manager is your primary point of contact:
```python
orch = get_orchestrator()
orth.spawn_agent('manager')

# Ask about team status
response = orch.chat_with_agent_sync('Manager', "Who's working on what?")

# Spawn a squad
response = orch.chat_with_agent_sync('Manager', "Spawn the creative squad")

# Create a new agent
response = orch.chat_with_agent_sync('Manager', "Create a data analyst named Atlas")
```

### Dynamic Agent Creation (NEW)
```python
from shared.agent_factory import agent_factory

# From template
soul_path = agent_factory.create_agent_from_template(
    template_key="data_analyst",
    name="Atlas"
)

# Custom agent
soul_path = agent_factory.create_custom_agent(
    name="Zeus",
    role="Cloud Architect", 
    avatar="☁️",
    essence="Cloud infrastructure expert...",
    skills=["AWS", "Terraform", "Kubernetes"],
    model="qwen3-coder"
)

# Spawn the new agent
orch.spawn_agent(soul_path.parent.name)
```

### Spawn an Agent
```python
from workspace_orchestrator import get_orchestrator
orch = get_orchestrator()
agent = orch.spawn_agent('shuri')  # Returns AgentRunner thread
```

### Create Mission
```python
mission = orch.create_mission(
    title="Project Name",
    description="Goal description",
    tasks=[
        {"description": "Task 1", "assigned_to": "Shuri"},
        {"description": "Task 2", "assigned_to": "Quill"}
    ]
)
```

### Execute Mission
```python
# Parallel execution (all tasks at once)
orth.execute_mission_parallel(mission.id)

# Individual task assignment
orch.assign_task("Shuri", "Task description", mission.id, task.id)
```

### Chat with Agent
```python
# Sync chat with 30s timeout
response = orch.chat_with_agent_sync(agent_id, "Hello")
```

## Testing

### QA Tests (12/12 passing)
Run: `python3 test_full_qa.py`
- Agent spawning
- Mission creation
- Task assignment
- Chat functionality
- Export generation

### Project Test
Full end-to-end with creative team:
```bash
python3 << 'EOF'
from workspace_orchestrator import get_orchestrator
orch = get_orchestrator()

# Spawn team
team = ['shuri', 'pixel', 'code', 'quill']
for name in team:
    orch.spawn_agent(name)

# Create mission
mission = orch.create_mission(
    title="Landing Page Project",
    description="Create landing page copy",
    tasks=[
        {"description": "Write product positioning", "assigned_to": "Shuri"},
        {"description": "Write landing page headline", "assigned_to": "Quill"},
        {"description": "Design mockup", "assigned_to": "Pixel"}
    ]
)

# Execute
orch.execute_mission_parallel(mission.id)
EOF
```

## Known Issues

1. **Chat History Empty**: Persistence logic needs verification
2. **Activity Tracker**: No events captured during execution
3. **Timeout**: Long tasks may hit 60s default timeout
4. **Memory**: Agent memory files not populating

## File Locations

| Data Type | Location |
|-----------|----------|
| Missions | `./missions/*.json` |
| Agent Memory | `./memory/*.jsonl` |
| Chat History | `./chat_history/*.json` |
| Exports | `./exports/*.md` |
| Agent Souls | `./agents/{name}/soul.md` |
| Logs | `./logs/` |

## Configuration

Environment variables in `.env`:
```
OLLAMA_HOST=http://herbie:11434
WORKSPACE_DATA_DIR=./data
```

## Version History

- **v1.6.1** (Current): Collapsible HUD, fixed navigation, cleaner UI
- **v1.6.0**: HUD redesign, floating dashboard, chat-first interface
- **v1.5.0**: Manager Overseer, dynamic agent creation, thinking animations
- **v1.4.0**: Resource monitoring, individual agent controls, better UX
- **v1.3.0**: MVP Complete - Parallel execution, exports, handoffs
- **v1.2.0**: Thread-based agents, persistent chat
- **v1.1.0**: Mission system, basic task execution
- **v1.0.0**: Initial release, single agent chat
