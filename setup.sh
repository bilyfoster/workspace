#!/bin/bash
#
# Workspace Setup Script for macOS
# One-command setup for Mac users
#

set -e

echo "🎯 Workspace Setup for macOS"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${YELLOW}Warning: This script is optimized for macOS${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check Python
echo "📦 Step 1: Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Please install Python 3.9 or higher:"
    echo "  brew install python@3.11"
    exit 1
fi

# Step 2: Check Ollama
echo ""
echo "🦙 Step 2: Checking Ollama installation..."
if command_exists ollama; then
    echo -e "${GREEN}✓ Ollama found${NC}"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is running${NC}"
        
        # List available models
        echo ""
        echo "Available models:"
        curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | sed 's/"name":"/  - /;s/"//' || echo "  (Could not fetch models)"
    else
        echo -e "${YELLOW}⚠ Ollama is installed but not running${NC}"
        echo "Start Ollama with: ollama serve"
        read -p "Start Ollama now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Starting Ollama..."
            ollama serve &
            sleep 3
        fi
    fi
else
    echo -e "${YELLOW}⚠ Ollama not found${NC}"
    echo "Install Ollama:"
    echo "  1. Download from: https://ollama.com/download/Ollama-darwin.zip"
    echo "  2. Or run: brew install ollama"
    exit 1
fi

# Step 3: Create virtual environment
echo ""
echo "🐍 Step 3: Setting up Python environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Step 4: Install dependencies
echo ""
echo "📥 Step 4: Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 5: Create necessary directories
echo ""
echo "📁 Step 5: Creating directories..."
mkdir -p logs missions agents/{hunter,pepper,scout,sage,shuri,quill,wong,code,pixel,guardian,lingua}/{memory,knowledge}
touch agents/.gitkeep
echo -e "${GREEN}✓ Directories created${NC}"

# Step 6: Configure for macOS
echo ""
echo "⚙️  Step 6: Configuring for macOS..."
if [ ! -f "config.local.yaml" ]; then
    cat > config.local.yaml << 'EOF'
# Local macOS Configuration
ollama:
  host: "http://localhost:11434"
  default_model: "qwen3.5:9b"
  orchestrator_model: "qwen3.5:9b"
  timeout: 120

agents:
  max_concurrent: 5
  always_alive: true
  temperature: 0.7

missions:
  storage_path: "./missions"
  auto_save: 30

interface:
  default: "cli"
  telegram_token: null

logging:
  level: "INFO"
  file: "./logs/workspace.log"
  max_size_mb: 10
  backup_count: 5
EOF
    echo -e "${GREEN}✓ Created config.local.yaml${NC}"
fi

# Step 7: Create launch script
echo ""
echo "🚀 Step 7: Creating launch scripts..."
cat > start.sh << 'EOF'
#!/bin/bash
# Workspace Launch Script for macOS

cd "$(dirname "$0")"

# Check if already running
if pgrep -f "streamlit run dashboard.py" > /dev/null; then
    echo "⚠️  Workspace is already running!"
    echo "   Access at: http://localhost:8501"
    echo "   Or run: ./stop.sh to stop it first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "🦙 Starting Ollama..."
    ollama serve &
    sleep 3
fi

echo "🎯 Starting Workspace..."
echo "   Dashboard will be available at: http://localhost:8501"
echo ""

# Start Workspace
streamlit run dashboard.py --server.headless false
EOF
chmod +x start.sh

cat > stop.sh << 'EOF'
#!/bin/bash
# Stop Workspace
echo "🛑 Stopping Workspace..."
pkill -f "streamlit run dashboard.py" 2>/dev/null || true
echo "✓ Workspace stopped"
EOF
chmod +x stop.sh

cat > status.sh << 'EOF'
#!/bin/bash
# Check Workspace status

echo "🎯 Workspace Status"
echo "==================="
echo ""

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "🦙 Ollama: ✅ Running"
else
    echo "🦙 Ollama: ❌ Not running"
fi

# Check Workspace
if pgrep -f "streamlit run dashboard.py" > /dev/null; then
    echo "🎯 Dashboard: ✅ Running at http://localhost:8501"
else
    echo "🎯 Dashboard: ❌ Not running"
fi

echo ""
echo "Commands:"
echo "  ./start.sh  - Start Workspace"
echo "  ./stop.sh   - Stop Workspace"
echo "  ./status.sh - Check status"
EOF
chmod +x status.sh

echo -e "${GREEN}✓ Launch scripts created${NC}"

# Done
echo ""
echo "=============================="
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo "Quick start:"
echo "  1. ./start.sh     # Start Workspace"
echo "  2. Open browser to: http://localhost:8501"
echo "  3. ./stop.sh      # Stop Workspace"
echo ""
echo "Or use the CLI:"
echo "  python main.py"
echo ""
