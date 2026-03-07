#!/bin/bash
# Double-clickable installer for macOS
# This script runs when you double-click it in Finder

cd "$(dirname "$0")"

# Open Terminal and run setup
osascript <<EOF
tell application "Terminal"
    do script "cd '$(pwd)'; ./setup.sh"
    activate
end tell
EOF
