# Makefile for Workspace
# Simple commands for Mac users

.PHONY: help install start stop status clean update

help:
	@echo "🎯 Workspace Commands"
	@echo "===================="
	@echo ""
	@echo "Setup:"
	@echo "  make install    - First-time setup"
	@echo ""
	@echo "Run:"
	@echo "  make start      - Start the dashboard"
	@echo "  make stop       - Stop all services"
	@echo "  make status     - Check what's running"
	@echo "  make restart    - Restart services"
	@echo ""
	@echo "Development:"
	@echo "  make update     - Pull latest code from GitHub"
	@echo "  make logs       - View recent logs"
	@echo "  make clean      - Clean up temporary files"
	@echo ""
	@echo "CLI Mode:"
	@echo "  make cli        - Run command-line interface"

install:
	@echo "🔧 Running setup..."
	@./setup.sh

start:
	@echo "🚀 Starting Workspace..."
	@./start.sh

stop:
	@echo "🛑 Stopping Workspace..."
	@./stop.sh

status:
	@echo "📊 Checking status..."
	@./status.sh

restart: stop start

update:
	@echo "📥 Pulling latest changes..."
	@git pull origin main
	@echo "📦 Updating dependencies..."
	@venv/bin/pip install -r requirements.txt
	@echo "✅ Updated!"

logs:
	@echo "📋 Recent logs:"
	@tail -n 50 logs/workspace.log 2>/dev/null || echo "No logs found"

clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@echo "✅ Cleaned!"

cli:
	@echo "🖥️  Starting CLI..."
	@venv/bin/python main.py

# Quick commands
dev:
	@make start

serve:
	@venv/bin/streamlit run dashboard.py

# Docker commands (if we add Docker later)
docker-build:
	@echo "Building Docker image..."
	@docker build -t workspace .

docker-run:
	@echo "Running in Docker..."
	@docker run -p 8501:8501 --network host workspace
