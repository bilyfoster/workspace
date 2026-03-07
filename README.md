# 🎯 Workspace

**A local, self-hosted AI Mission Control system.**

Deploy a squad of specialized AI agents — each with their own personality, memory, and soul — working together on any goal. Runs entirely on your hardware using Ollama.

> **Built for Herbie** - Your local AI server

---

## 🌟 What Makes Workspace Different

Unlike other systems that just swap prompts, Workspace agents are **full sub-processes** with:

- **🧬 soul.md** - Each agent has a manifest defining identity, values, and personality
- **🧠 Persistent Memory** - Agents remember conversations and learn over time
- **🔧 True Isolation** - Each agent runs independently (crash one, others keep working)
- **⚡ Multi-Model** - Hunter can use `dolphin3` (creative) while Code uses `qwen3-coder` (precise)
- **📡 Activity Monitoring** - See who's talking to whom in real-time
- **🔄 Agent Handoffs** - Agents collaborate by passing tasks to each other
- **📊 Mission Control Dashboard** - Trello-style board for monitoring missions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKSPACE ORCHESTRATOR                        │
│              (Coordinates missions, manages agents)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Message Bus (IPC)
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Hunter    │     │   Pepper    │     │    Code     │
│  (Sales)    │     │  (Email)    │     │   (Dev)     │
│             │     │             │     │             │
│  soul.md    │     │  soul.md    │     │  soul.md    │
│  memory/    │     │  memory/    │     │  memory/    │
│  Process    │     │  Process    │     │  Process    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              Individual Ollama Connections
               (Different models per agent)
```

---

## 🚀 Quick Start

### 1. Install

```bash
cd /Users/bilyfoster/source/workspace
pip install -r requirements.txt
```

### 2. Configure

Edit `config.yaml`:
```yaml
ollama:
  host: "http://herbie:11434"  # Your Ollama server
```

### 3. Launch Dashboard

```bash
streamlit run dashboard.py
```

Then open http://localhost:8501

---

## 🎮 Using Workspace

### Dashboard Interface

The dashboard gives you a **Mission Control** view:

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 WORKSPACE - Mission Control Dashboard                    │
├─────────────────────────────────────────────────────────────┤
│  👥 Active Squad          │  📋 Mission Board                │
│  🟢 Hunter - Idle         │  ┌─────────┬─────────┬────────┐ │
│  🔵 Pepper - Working      │  │ 📥 To Do│ 🔵 Doing│ ✅ Done│ │
│  🟢 Code - Idle           │  │ Task 1  │ Task 2  │ Task 3 │ │
│                           │  └─────────┴─────────┴────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Spawn Agents

1. Go to **Agents** tab
2. Select agents to spawn (Hunter, Pepper, Code, etc.)
3. Click "Spawn Selected Agents"

Or use quick squad buttons:
- 🎯 **Sales Squad** - Hunter + Pepper + Sage
- 🎨 **Creative Squad** - Quill + Pixel + Pepper
- 💻 **Dev Squad** - Code + Guardian + Wong

### Create a Mission

1. Go to **Create Mission** tab
2. Enter mission title and description
3. Add tasks with assigned agents (or auto-assign)
4. Click "Launch Mission"

### Execute Tasks

1. Go to **Missions** tab
2. Select your mission
3. Click "Assign & Execute" on pending tasks
4. Watch agents work in real-time!

---

## 👥 Meet the Squad

| Agent | Avatar | Role | Soul Focus | Model |
|-------|--------|------|------------|-------|
| **Hunter** | 🎯 | Sales & Outreach | Opens doors, starts conversations | dolphin3 |
| **Pepper** | 📧 | Email Marketing | Data-driven campaigns | dolphin3 |
| **Quill** | 📝 | Social Media | Scroll-stopping content | gemma3 |
| **Shuri** | 🎯 | Product Strategy | User-obsessed roadmaps | qwen3.5:9b |
| **Wong** | 📚 | Documentation | Makes complex simple | qwen3-coder:30b |
| **Code** | 💻 | Software Dev | Clean, maintainable code | qwen3-coder:30b |
| **Scout** | 🔍 | Research | Finds what others miss | qwen3.5:9b |
| **Sage** | 📊 | Data Analyst | Insights from noise | qwen3.5:9b |
| **Pixel** | 🎨 | UI/UX Design | Champions the user | gemma3 |
| **Guardian** | 🛡️ | QA & Testing | Breaks before users do | qwen3-coder:30b |
| **Lingua** | 🌍 | Localization | Bridges cultures | qwen3.5:35b |

---

## 🗂️ Project Structure

```
workspace/
├── agents/                      # Agent souls & memories
│   ├── hunter/
│   │   ├── soul.md             # Identity, values, personality
│   │   ├── memory/             # Conversation history
│   │   └── knowledge/          # Learned patterns
│   ├── pepper/
│   └── ... (11 agents total)
├── shared/
│   └── bus/                    # Inter-agent message bus
├── herbie/                     # Legacy (being migrated)
├── workspace_orchestrator.py   # Main orchestrator
├── agent_process.py            # Sub-agent runner
├── dashboard.py                # Streamlit UI
├── config.yaml                 # Configuration
└── missions/                   # Mission storage
```

---

## 🧬 Creating Custom Agents

Create a new agent by adding a directory to `agents/`:

```bash
mkdir agents/myagent
touch agents/myagent/soul.md
```

**soul.md template:**

```markdown
# MyAgent - Soul Manifest

## Core Identity
**Name:** MyAgent
**Role:** Specialist
**Avatar:** 🎭

## Essence
Who are you? What drives you?

## Personality Traits
- Trait 1
- Trait 2

## Core Values
1. Value 1
2. Value 2

## Expertise
- Skill 1
- Skill 2

## Model Configuration
```yaml
model: gemma3:latest
temperature: 0.7
```

## Memory
- **Long-term:** `/agents/myagent/memory/`
```

Restart the dashboard and your agent appears in the spawn list!

---

## 🔧 Resource Usage

| Component | RAM Usage | Notes |
|-----------|-----------|-------|
| Orchestrator | ~50MB | Central coordination |
| Each Agent | ~30MB | Python process + memory |
| Ollama Model | 4-16GB | Depends on model loaded |
| **Total (3 agents)** | ~6-10GB | With qwen3.5:9b |

---

## 🛣️ Roadmap

- [x] Full sub-agent processes with soul.md
- [x] Persistent agent memory
- [x] Message bus for inter-agent communication
- [x] Mission Control dashboard
- [ ] Agent-to-agent handoffs
- [ ] Tool integration (web search, file operations)
- [ ] Parallel task execution
- [ ] Telegram bot interface
- [ ] REST API
- [ ] Agent learning/self-improvement

---

## 📝 License

MIT - Build your own AI squad!

---

**Built with ❤️ for Herbie**
