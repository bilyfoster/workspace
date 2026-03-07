# 🎯 Workspace

**AI Mission Control for macOS**

Deploy a squad of specialized AI agents — each with their own personality, memory, and soul — working together on any goal. Runs entirely on your Mac using Ollama.

> **Built for Mac users** who want local AI collaboration without the cloud.

---

## 🚀 Quick Start (3 Steps)

```bash
# 1. Clone
git clone https://github.com/bilyfoster/workspace.git
cd workspace

# 2. Setup (one-time)
./setup.sh

# 3. Start
./start.sh
```

Then open **http://localhost:8501** 🎉

**Even easier:** Double-click `install.command`

---

## 🎥 See It In Action

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 WORKSPACE v1.1.0 - Mission Control Dashboard            │
├─────────────────────────────────────────────────────────────┤
│  👥 Active Squad          │  📋 Mission Board                │
│  🟢 Hunter - Idle         │  ┌─────────┬─────────┬────────┐ │
│  🔵 Pepper - Working      │  │ 📥 To Do│ 🔵 Doing│ ✅ Done│ │
│  🟢 Scout - Idle          │  │ Task 1  │ Task 2  │ Task 3 │ │
│                           │  └─────────┴─────────┴────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🤖 True AI Agents
- **soul.md** - Each agent has identity, values, and personality
- **Persistent Memory** - Agents remember conversations
- **Sub-process Architecture** - Real isolation, not just prompt swapping
- **Multi-model** - Hunter uses `dolphin3` (creative), Code uses `qwen3-coder` (precise)

### 🔄 Agent Collaboration
- **Handoffs** - Agents pass work with full context
- **Group Chats** - Multiple agents in one conversation
- **Auto-handoffs** - AI detects when to delegate

### 📊 Mission Control
- **Dashboard** - Trello-style mission boards
- **Activity Feed** - Real-time event monitoring
- **Analytics** - Performance charts and metrics
- **Alerts** - Configurable notifications

### 💻 Mac Native
- **No Docker** - Direct hardware access
- **Metal GPU** - Uses Apple's GPU acceleration via Ollama
- **Simple Scripts** - `./start.sh`, `./stop.sh`, `./status.sh`
- **Make commands** - `make start`, `make stop`

---

## 🛠️ Installation

### Prerequisites

1. **macOS 10.15+**
2. **Python 3.9+** (usually pre-installed: `python3 --version`)
3. **Ollama** - [Download](https://ollama.com/download) or `brew install ollama`

### Option 1: Double-Click (Easiest)

Double-click `install.command` and follow prompts.

### Option 2: Terminal

```bash
git clone https://github.com/bilyfoster/workspace.git
cd workspace
./setup.sh
```

### Option 3: Make

```bash
git clone https://github.com/bilyfoster/workspace.git
cd workspace
make install
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup.

---

## 🎮 Usage

### Start Workspace

```bash
./start.sh
# or
make start
```

Opens **http://localhost:8501** automatically.

### Daily Commands

```bash
make start    # Start dashboard
make stop     # Stop everything
make status   # Check what's running
make restart  # Restart
make update   # Pull latest from GitHub
```

### First Mission

1. Go to **🤖 Agents** tab
2. Click **"Spawn Sales Squad"**
3. Go to **➕ Create Mission**
4. Enter: *"Launch email campaign for new product"*
5. Watch Hunter, Pepper, and Scout collaborate!

---

## 👥 Meet Your Squad

| Agent | Role | Specialty | Best For |
|-------|------|-----------|----------|
| **Hunter** | 🎯 Sales | Outreach, cold email | Opening doors |
| **Pepper** | 📧 Marketing | Email campaigns | Converting leads |
| **Quill** | 📝 Social | Content creation | Engagement |
| **Scout** | 🔍 Research | Market intel | Finding answers |
| **Sage** | 📊 Data | Analytics | Insights |
| **Shuri** | 🎯 Product | Strategy | Roadmaps |
| **Code** | 💻 Developer | Coding | Building features |
| **Wong** | 📚 Docs | Technical writing | Documentation |
| **Pixel** | 🎨 Design | UI/UX | User experience |
| **Guardian** | 🛡️ QA | Testing | Quality |
| **Lingua** | 🌍 Translator | Localization | Global reach |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           YOUR MAC                      │
│  ┌─────────────────────────────────┐    │
│  │   Ollama (Metal GPU)            │    │
│  │   - Local LLM inference         │    │
│  │   - 7-35B parameter models      │    │
│  └─────────────────────────────────┘    │
│                   ↑                     │
│  ┌─────────────────────────────────┐    │
│  │   Workspace (Native Python)     │    │
│  │   - Sub-agent processes         │    │
│  │   - Streamlit dashboard         │    │
│  │   - Message bus                 │    │
│  └─────────────────────────────────┘    │
│                   ↑                     │
│         http://localhost:8501           │
└─────────────────────────────────────────┘
```

**Why not Docker?**
- Zero overhead - direct Metal GPU access
- Simpler setup - no container configuration
- Native process management - easier debugging
- 1GB+ less RAM usage

---

## 📁 Project Structure

```
workspace/
├── start.sh              ← Start here
├── stop.sh               ← Stop everything
├── setup.sh              ← One-time setup
├── Makefile              ← Make commands
├── install.command       ← Double-click installer
├── QUICKSTART.md         ← Quick start guide
│
├── dashboard.py          ← Streamlit UI
├── workspace_orchestrator.py
├── agent_process.py      ← Sub-agent runner
│
├── agents/               ← Agent souls
│   ├── hunter/soul.md
│   ├── pepper/soul.md
│   └── ... (11 total)
│
├── shared/bus/           ← Communication
│   ├── message_bus.py
│   ├── handoff.py
│   ├── group_chat.py
│   ├── alerts.py
│   ├── analytics.py
│   └── auto_handoff.py
│
├── soul.md               ← Project identity
├── README.md             ← This file
└── FEATURES.md           ← Feature docs
```

---

## 🛣️ Roadmap

- [x] Sub-agent architecture with soul.md
- [x] Agent handoffs
- [x] Group chat
- [x] Activity monitoring
- [x] Analytics & charts
- [x] Mac-friendly setup
- [ ] Telegram bot
- [ ] REST API
- [ ] iOS companion app
- [ ] Siri integration

---

## 🤝 Contributing

1. Fork it
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -am 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Create Pull Request

---

## 📝 License

MIT License - Build your own AI squad!

---

**Built with ❤️ for Mac users by [bilyfoster](https://github.com/bilyfoster)**

Version: v1.1.0 | [GitHub](https://github.com/bilyfoster/workspace) | [Issues](https://github.com/bilyfoster/workspace/issues)
