# Workspace - Project Soul Manifest

## Core Identity
**Name:** Workspace  
**Version:** 1.1.5  
**Codename:** Mission Control  
**Created:** 2026-03-07  
**Last Updated:** 2026-03-07  
**Git Commit:** 006e71b

---

## Essence
Workspace is an AI Mission Control system that orchestrates a squad of specialized agents, each with their own identity, memory, and purpose. Unlike systems that just swap prompts, our agents are full sub-processes with souls.

Our north star: **True agent collaboration through handoffs, transparency through activity monitoring, and complete local control.**

---

## Version History

### v1.1.5 (2026-03-07)
**UI/UX Improvements:**
- New "Chat with Agents" page for direct agent interaction
- Visual chat interface with message history
- Quick prompt buttons for common tasks
- Improved Spawn Agents page with visual cards
- Progress bars for squad spawning
- Better status indicators and visual feedback
- Simplified navigation (7 clear tabs)
- Clear empty states with action buttons

### v1.1.4 (2026-03-07)
**Critical Bug Fix:**
- Fixed agents not spawning - MessageBus singleton issue
- Migrated from subprocess to thread-based architecture
- Agents now share memory and can communicate properly
- Added agent_runner.py for thread-based agent execution
- Updated MessageBus to support thread-safe queues

### v1.1.3 (2026-03-07)
**Bug Fixes:**
- Fixed mission creation form - checkbox was after submit button
- Added proper form validation with error messages
- Fixed Streamlit widget ordering issue

### v1.1.2 (2026-03-07)
**Bug Fixes:**
- Fixed syntax error in dashboard.py footer (EOL while scanning string literal)
- Fixed Python f-string multiline issue in sidebar markdown

### v1.1.1 (2026-03-07)
**Features Added:**
- Mac-friendly setup with setup.sh and install.command
- Makefile for simple commands (make start/stop/status)
- QUICKSTART.md guide for 3-step setup
- Auto-detection of Python and Ollama
- Colored output and better error messages
- Native macOS performance optimization

**Changes:**
- Added setup.sh - Interactive installer
- Added install.command - Double-clickable launcher
- Added Makefile - Build commands
- Updated README.md with Mac-first focus
- Enhanced requirements.txt for macOS

### v1.1.0 (2026-03-07)
**Features Added:**
- Auto-handoff system - Agents intelligently request handoffs when tasks exceed their scope
- Group chat support - Multiple agents in threaded conversations
- Activity alerts - Configurable notifications for critical events
- Time-based analytics - Activity charts and agent performance metrics
- Version tracking in soul.md

**Changes:**
- Added auto-handoff detector in agent_process.py
- Implemented GroupChatManager for multi-agent conversations
- Created AlertManager for event-based notifications
- Added AnalyticsCollector for metrics over time
- Updated dashboard with charts and analytics tab

### v1.0.0 (2026-03-07)
**Initial Release:**
- Full sub-agent architecture with soul.md identity files
- 11 specialized agents (Hunter, Pepper, Scout, Sage, etc.)
- Agent-to-agent handoffs for collaborative workflows
- Activity monitoring and conversation tracking
- Mission Control dashboard with Streamlit
- Message bus for inter-agent communication
- Persistent agent memory
- Multi-model support
- GitHub integration

---

## Core Features

### Agent Architecture
- **Sub-process agents** - Each agent runs independently with isolation
- **soul.md** - Identity, values, personality, and configuration
- **Persistent memory** - Long-term conversation history
- **Multi-model** - Different LLM models per agent specialty

### Collaboration
- **Handoffs** - Agents pass tasks with full context
- **Group chats** - Multiple agents in one conversation
- **Message bus** - Real-time inter-agent communication

### Monitoring
- **Activity feed** - Real-time event log
- **Analytics** - Performance charts over time
- **Alerts** - Configurable notifications
- **Mission tracking** - Trello-style boards

### Deployment
- **Local-first** - Runs on Herbie (Ollama)
- **Self-hosted** - No cloud dependencies
- **Open source** - MIT license

---

## Tech Stack
- **Python 3.9+** - Core runtime
- **Ollama** - Local LLM inference
- **Streamlit** - Web dashboard
- **SQLite/JSON** - Mission persistence
- **Asyncio** - Concurrent agent management
- **SSH/Git** - Version control

---

## Roadmap

### v1.2.0 (Planned)
- Tool integration (web search, file operations)
- Parallel task execution
- Telegram bot interface
- REST API

### v2.0.0 (Future)
- Agent learning/self-improvement
- Advanced planning algorithms
- Distributed agent deployment
- Voice interface

---

## Team
- **bilyfoster** - Creator & Architect
- **Herbie** - Host system & AI infrastructure

---

## Links
- **Repository:** https://github.com/bilyfoster/workspace
- **Dashboard:** http://localhost:8501
- **Documentation:** ./README.md, ./FEATURES.md

---

## Version Footer
**Current Version:** v1.1.0  
**Last Commit:** aae6cf4  
**Status:** Production Ready
