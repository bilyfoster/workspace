#!/usr/bin/env python3
"""
Herbie - AI Squad Leader
Local Agent Orchestration System

Usage:
    python main.py              # Start interactive CLI
    python main.py --help       # Show help
"""
import sys
from pathlib import Path

# Add herbie to path
sys.path.insert(0, str(Path(__file__).parent))

from herbie.interfaces.cli import main

if __name__ == "__main__":
    main()
