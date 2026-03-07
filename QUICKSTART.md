# 🚀 Quick Start for Mac Users

Get Workspace running in 3 steps.

---

## Prerequisites

1. **macOS** (10.15 or later recommended)
2. **Python 3.9+** (usually pre-installed)
3. **Ollama** - [Download here](https://ollama.com/download)

---

## Option 1: Double-Click Install (Easiest)

1. **Double-click** `install.command`
2. Follow prompts in Terminal
3. Done!

---

## Option 2: Terminal Install

```bash
# 1. Clone the repository
git clone https://github.com/bilyfoster/workspace.git
cd workspace

# 2. Run setup
./setup.sh

# 3. Start Workspace
./start.sh
```

Your browser will open automatically to: **http://localhost:8501**

---

## Option 3: Make Commands

```bash
# Clone and enter directory
git clone https://github.com/bilyfoster/workspace.git
cd workspace

# Install
make install

# Start
make start

# Check status
make status

# Stop
make stop
```

---

## First Time Setup Checklist

After installation:

- [ ] Pull some Ollama models:
  ```bash
  ollama pull qwen3.5:9b
  ollama pull gemma3:latest
  ollama pull dolphin3:latest
  ```

- [ ] Open http://localhost:8501

- [ ] Click "🤖 Agents" → "Spawn Sales Squad"

- [ ] Click "➕ Create Mission" → Enter a mission

- [ ] Watch your agents collaborate! 🎉

---

## Daily Commands

```bash
# Start Workspace
./start.sh

# Or with Make
make start

# Access dashboard
open http://localhost:8501

# Stop when done
./stop.sh
```

---

## Troubleshooting

### "Port 8501 already in use"
```bash
./stop.sh
# or
make stop
# Then restart
```

### "Ollama not found"
```bash
# Install Ollama
brew install ollama
# or download from https://ollama.com/download
```

### "Permission denied"
```bash
chmod +x setup.sh start.sh stop.sh
```

### Models not showing up
```bash
# Pull a model
ollama pull qwen3.5:9b

# List models
ollama list
```

---

## What's Running?

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:8501 | Web UI |
| Ollama | http://localhost:11434 | AI models |

---

## Folder Structure

```
workspace/
├── start.sh          ← Start here
├── stop.sh           ← Stop everything
├── setup.sh          ← One-time setup
├── Makefile          ← Make commands
├── dashboard.py      ← Main app
├── agents/           ← Agent souls
├── missions/         ← Saved missions
└── logs/             ← Log files
```

---

## Need Help?

- 📖 Full docs: [README.md](README.md)
- 🎨 Features: [FEATURES.md](FEATURES.md)
- 🐛 Issues: https://github.com/bilyfoster/workspace/issues

---

**You're ready to build your AI squad!** 🎯
