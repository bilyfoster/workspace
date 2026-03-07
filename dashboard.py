#!/usr/bin/env python3
"""
Workspace Dashboard v1.6.0 - HUD Overlay Design

A floating HUD dashboard overlaying the main chat interface.
- HUD: Status metrics and agent mini-cards (floating)
- Chat History: Scrollable conversation (main area)
- Input: Bottom chat input

Usage:
    streamlit run dashboard.py

Version: v1.6.0
"""
import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from workspace_orchestrator import get_orchestrator
from shared.bus.activity_tracker import tracker
from shared.resource_monitor import resource_monitor
from shared.agent_factory import agent_factory

# Page config
st.set_page_config(
    page_title="Workspace | HUD v1.6.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== HUD-STYLE CSS ====================
st.markdown("""
<style>
    /* Hide default Streamlit elements for HUD feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container adjustments */
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    
    /* Floating HUD Panel */
    .hud-panel {
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        width: 95%;
        max-width: 1400px;
        background: rgba(20, 20, 30, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 16px 24px;
        z-index: 1000;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    
    /* HUD Header */
    .hud-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 12px;
    }
    
    .hud-title {
        font-size: 1.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* HUD Metrics */
    .hud-metrics {
        display: flex;
        gap: 24px;
    }
    
    .hud-metric {
        text-align: center;
        color: white;
    }
    
    .hud-metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #667eea;
        line-height: 1;
    }
    
    .hud-metric-label {
        font-size: 0.7rem;
        color: rgba(255, 255, 255, 0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }
    
    .hud-metric-working {
        color: #ffc107;
        animation: pulse-yellow 2s infinite;
    }
    
    .hud-metric-alert {
        color: #ff4757;
        animation: pulse-red 1s infinite;
    }
    
    @keyframes pulse-yellow {
        0%, 100% { opacity: 1; text-shadow: 0 0 5px rgba(255, 193, 7, 0.5); }
        50% { opacity: 0.8; text-shadow: 0 0 15px rgba(255, 193, 7, 0.8); }
    }
    
    @keyframes pulse-red {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Agent Mini Cards */
    .hud-agents {
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding: 8px 0;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.2) transparent;
    }
    
    .hud-agent-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        min-width: 140px;
        border: 2px solid transparent;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .hud-agent-card:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
    }
    
    .hud-agent-card.idle {
        border-color: #2ed573;
    }
    
    .hud-agent-card.working {
        border-color: #ffc107;
        animation: card-glow 2s infinite;
    }
    
    .hud-agent-card.error {
        border-color: #ff4757;
    }
    
    @keyframes card-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255, 193, 7, 0.3); }
        50% { box-shadow: 0 0 15px rgba(255, 193, 7, 0.6); }
    }
    
    .hud-agent-avatar {
        font-size: 1.5rem;
        margin-bottom: 4px;
    }
    
    .hud-agent-name {
        font-size: 0.9rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .hud-agent-status {
        font-size: 0.7rem;
        color: rgba(255, 255, 255, 0.6);
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
    }
    
    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
    }
    
    .status-dot.idle { background: #2ed573; }
    .status-dot.working { 
        background: #ffc107; 
        animation: blink 1s infinite;
    }
    .status-dot.error { background: #ff4757; }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .hud-agent-task {
        font-size: 0.65rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 120px;
    }
    
    /* Chat Area - Below HUD */
    .chat-area {
        margin-top: 280px;
        padding: 20px;
        padding-bottom: 120px;
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Chat Messages */
    .chat-message {
        margin: 16px 0;
        animation: fade-in 0.3s ease;
    }
    
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .chat-message-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px 20px 4px 20px;
        padding: 16px 20px;
        margin-left: auto;
        max-width: 80%;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .chat-message-agent {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 20px 20px 20px 4px;
        padding: 16px 20px;
        margin-right: auto;
        max-width: 80%;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
    }
    
    .chat-message-header {
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .chat-message-user .chat-message-header {
        color: rgba(255, 255, 255, 0.9);
    }
    
    .chat-message-agent .chat-message-header {
        color: #667eea;
    }
    
    /* Thinking Indicator */
    .thinking-bubble {
        background: rgba(102, 126, 234, 0.1);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 20px;
        padding: 12px 20px;
        display: inline-flex;
        align-items: center;
        gap: 12px;
        animation: thinking-pulse 2s infinite;
    }
    
    @keyframes thinking-pulse {
        0%, 100% { border-color: rgba(102, 126, 234, 0.3); }
        50% { border-color: rgba(102, 126, 234, 0.6); }
    }
    
    .thinking-dots {
        display: flex;
        gap: 4px;
    }
    
    .thinking-dot {
        width: 8px;
        height: 8px;
        background: #667eea;
        border-radius: 50%;
        animation: dot-bounce 1.4s infinite ease-in-out both;
    }
    
    .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
    .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes dot-bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    /* Input Area - Fixed Bottom */
    .input-area {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        border-top: 1px solid rgba(0, 0, 0, 0.1);
        padding: 16px 24px;
        z-index: 999;
    }
    
    .input-container {
        max-width: 900px;
        margin: 0 auto;
        display: flex;
        gap: 12px;
        align-items: flex-end;
    }
    
    .chat-input {
        flex: 1;
        background: #f5f5f5;
        border: 2px solid transparent;
        border-radius: 24px;
        padding: 14px 20px;
        font-size: 1rem;
        outline: none;
        transition: all 0.3s;
    }
    
    .chat-input:focus {
        background: white;
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
    }
    
    .send-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s;
        font-size: 1.2rem;
    }
    
    .send-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Mode Selector */
    .mode-selector {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 1001;
        background: rgba(20, 20, 30, 0.95);
        border-radius: 12px;
        padding: 8px;
    }
    
    /* Sidebar toggle */
    .sidebar-toggle {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1001;
        background: rgba(20, 20, 30, 0.95);
        border-radius: 12px;
        padding: 8px 12px;
        color: white;
        cursor: pointer;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Welcome message */
    .welcome-message {
        text-align: center;
        padding: 60px 20px;
        color: rgba(0, 0, 0, 0.5);
    }
    
    .welcome-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 16px;
    }
    
    .welcome-hint {
        font-size: 1rem;
        line-height: 1.8;
    }
    
    /* System message */
    .system-message {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        text-align: center;
        color: rgba(0, 0, 0, 0.6);
        font-size: 0.9rem;
        margin: 16px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = get_orchestrator()
if 'tracker' not in st.session_state:
    st.session_state.tracker = tracker
if 'resource_monitor' not in st.session_state:
    st.session_state.resource_monitor = resource_monitor
    resource_monitor.start_monitoring(interval=5.0)
if 'agent_factory' not in st.session_state:
    st.session_state.agent_factory = agent_factory
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_mode' not in st.session_state:
    st.session_state.chat_mode = "manager"  # manager, individual, group
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None
if 'thinking' not in st.session_state:
    st.session_state.thinking = False

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def render_hud():
    """Render the floating HUD dashboard"""
    data = get_dashboard_data()
    if not data:
        return
    
    agents = data['agents']
    working_count = len([a for a in agents if a['status'] == 'working'])
    error_count = len([a for a in agents if a['status'] == 'error'])
    active_missions = len([m for m in data['missions'] if m['status'] == 'active'])
    total_tasks = sum(a['tasks_completed'] for a in agents)
    
    # Determine alert state
    alert_class = "hud-metric-alert" if error_count > 0 else ""
    
    agent_cards_html = ""
    for agent in agents[:8]:  # Show up to 8 agents
        status_class = agent['status']
        status_dot = f"<div class='status-dot {status_class}'></div>"
        task_info = f"<div class='hud-agent-task'>{agent.get('current_task', 'Idle')[:25]}...</div>" if agent.get('current_task') else ""
        
        agent_cards_html += f"""
        <div class="hud-agent-card {status_class}" onclick="selectAgent('{agent['id']}')">
            <div class="hud-agent-avatar">{agent['avatar']}</div>
            <div class="hud-agent-name">{agent['name']}</div>
            <div class="hud-agent-status">{status_dot} {agent['status'].upper()}</div>
            {task_info}
        </div>
        """
    
    if len(agents) > 8:
        agent_cards_html += f"<div style='color:rgba(255,255,255,0.5);padding:20px;'>+{len(agents)-8} more</div>"
    
    st.markdown(f"""
    <div class="hud-panel">
        <div class="hud-header">
            <div class="hud-title">🎯 Workspace HUD</div>
            <div class="hud-metrics">
                <div class="hud-metric">
                    <div class="hud-metric-value">{len(agents)}</div>
                    <div class="hud-metric-label">Agents</div>
                </div>
                <div class="hud-metric">
                    <div class="hud-metric-value {'hud-metric-working' if working_count > 0 else ''}">{working_count}</div>
                    <div class="hud-metric-label">Working</div>
                </div>
                <div class="hud-metric">
                    <div class="hud-metric-value {alert_class}">{error_count}</div>
                    <div class="hud-metric-label">Alerts</div>
                </div>
                <div class="hud-metric">
                    <div class="hud-metric-value">{active_missions}</div>
                    <div class="hud-metric-label">Missions</div>
                </div>
                <div class="hud-metric">
                    <div class="hud-metric-value">{total_tasks}</div>
                    <div class="hud-metric-label">Tasks Done</div>
                </div>
            </div>
        </div>
        <div class="hud-agents">
            {agent_cards_html if agent_cards_html else '<div style="color:rgba(255,255,255,0.5);padding:20px;">No agents active</div>'}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chat_history():
    """Render the scrollable chat history"""
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-message">
            <div class="welcome-title">🎩 Welcome to Workspace</div>
            <div class="welcome-hint">
                <b>Chat with your Manager</b> to orchestrate your team<br>
                <small>Try: "Spawn the creative squad" or "Create a data analyst named Atlas"</small><br><br>
                <small>Or click an agent card above to chat directly</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            if msg['role'] == 'user':
                st.markdown(f"""
                <div class="chat-message">
                    <div class="chat-message-user">
                        <div class="chat-message-header">You</div>
                        {msg['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif msg['role'] == 'system':
                st.markdown(f"""
                <div class="system-message">{msg['content']}</div>
                """, unsafe_allow_html=True)
            else:
                avatar = msg.get('avatar', '🤖')
                name = msg.get('name', 'Agent')
                st.markdown(f"""
                <div class="chat-message">
                    <div class="chat-message-agent">
                        <div class="chat-message-header">{avatar} {name}</div>
                        {msg['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Thinking indicator
    if st.session_state.thinking:
        st.markdown("""
        <div class="chat-message">
            <div class="thinking-bubble">
                <span>🧠 Thinking</span>
                <div class="thinking-dots">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def handle_message(message: str):
    """Process user message"""
    if not message.strip():
        return
    
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": message
    })
    
    st.session_state.thinking = True
    st.rerun()

def process_response():
    """Process and generate response"""
    if not st.session_state.thinking:
        return
    
    # Get the last user message
    last_msg = None
    for msg in reversed(st.session_state.messages):
        if msg['role'] == 'user':
            last_msg = msg['content']
            break
    
    if not last_msg:
        st.session_state.thinking = False
        return
    
    data = get_dashboard_data()
    if not data:
        st.session_state.messages.append({
            "role": "agent",
            "name": "System",
            "avatar": "⚠️",
            "content": "System error - please check connection"
        })
        st.session_state.thinking = False
        return
    
    # Determine who to talk to
    msg_lower = last_msg.lower()
    
    # Check if asking about specific agent
    target_agent = None
    for agent in data['agents']:
        if agent['name'].lower() in msg_lower:
            target_agent = agent
            break
    
    # Handle special commands
    if "who" in msg_lower and ("working" in msg_lower or "doing" in msg_lower):
        # Generate status summary
        summary = "**Current Team Status:**\n\n"
        for a in data['agents']:
            if a['status'] == 'working':
                summary += f"⚡ **{a['name']}**: {a.get('current_task', 'Working')[:40]}...\n"
            else:
                summary += f"☕ **{a['name']}**: {a['status']}\n"
        summary += f"\n📊 **{sum(a['tasks_completed'] for a in data['agents'])}** tasks completed today"
        
        st.session_state.messages.append({
            "role": "agent",
            "name": "Manager",
            "avatar": "🎩",
            "content": summary
        })
    
    elif "spawn" in msg_lower or "start" in msg_lower:
        spawned = []
        for agent_name in data.get('available_agents', []):
            if agent_name.lower() in msg_lower:
                result = st.session_state.orchestrator.spawn_agent(agent_name)
                if result:
                    resource_monitor.register_agent(result.id, result.name)
                    spawned.append(agent_name.title())
        
        if spawned:
            st.session_state.messages.append({
                "role": "agent",
                "name": "Manager",
                "avatar": "🎩",
                "content": f"✅ Spawned: {', '.join(spawned)}"
            })
        else:
            st.session_state.messages.append({
                "role": "agent",
                "name": "Manager",
                "avatar": "🎩",
                "content": "I couldn't find agents to spawn. Available: " + ", ".join(data.get('available_agents', []))
            })
    
    elif "create" in msg_lower and "agent" in msg_lower:
        st.session_state.messages.append({
            "role": "agent",
            "name": "Manager",
            "avatar": "🎩",
            "content": "To create a new agent, go to **🤖 Agents** page and use the 'Create Agent' section.\n\nI can create agents with templates like:\n• Data Analyst 📊\n• DevOps Engineer 🔧\n• UX Researcher 🧪\n• Or fully custom agents!"
        })
    
    elif target_agent:
        # Chat with specific agent
        with st.spinner():
            response = st.session_state.orchestrator.chat_with_agent_sync(
                target_agent['name'], last_msg, timeout=30
            )
        
        if response:
            st.session_state.messages.append({
                "role": "agent",
                "name": target_agent['name'],
                "avatar": target_agent['avatar'],
                "content": response
            })
        else:
            st.session_state.messages.append({
                "role": "agent",
                "name": target_agent['name'],
                "avatar": target_agent['avatar'],
                "content": "❌ I'm not responding right now. Try respawning me."
            })
    
    else:
        # Default: Try to find Manager or use first available agent
        manager = next((a for a in data['agents'] if a['name'] == 'Manager'), None)
        target = manager if manager else (data['agents'][0] if data['agents'] else None)
        
        if target:
            with st.spinner():
                response = st.session_state.orchestrator.chat_with_agent_sync(
                    target['name'], last_msg, timeout=30
                )
            
            if response:
                st.session_state.messages.append({
                    "role": "agent",
                    "name": target['name'],
                    "avatar": target['avatar'],
                    "content": response
                })
            else:
                st.session_state.messages.append({
                    "role": "system",
                    "content": "⚠️ No response from agents. They may be offline or busy."
                })
        else:
            st.session_state.messages.append({
                "role": "system",
                "content": "🤖 No agents available. Go to 🤖 Agents page to spawn some!"
            })
    
    st.session_state.thinking = False

# ==================== MAIN APP ====================

# Process any pending response
if st.session_state.thinking:
    process_response()
    st.rerun()

# Render HUD (floating)
render_hud()

# Render chat history
render_chat_history()

# Render input area (fixed bottom)
with st.container():
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 1])
    
    with col1:
        message = st.text_input(
            "Message",
            placeholder="Ask Manager to spawn agents, create missions, or chat with team...",
            label_visibility="collapsed",
            key="chat_input"
        )
    
    with col2:
        if st.button("📤", use_container_width=True, key="send_btn"):
            if message:
                handle_message(message)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Handle enter key
if message and st.session_state.get('chat_input') != message:
    handle_message(message)

# Sidebar (collapsed by default, accessible via toggle)
with st.sidebar:
    st.markdown("# 🎯 Workspace v1.6.0")
    
    data = get_dashboard_data()
    if data:
        st.markdown("---")
        st.markdown("### 🎩 Manager Controls")
        
        if st.button("🚀 Spawn Manager", use_container_width=True):
            result = st.session_state.orchestrator.spawn_agent('manager')
            if result:
                resource_monitor.register_agent(result.id, result.name)
                st.success("Manager spawned!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ⚡ Quick Squads")
        
        squads = {
            "🎯 Sales": ['hunter', 'pepper', 'sage'],
            "🎨 Creative": ['quill', 'pixel', 'shuri'],
            "💻 Dev": ['code', 'guardian', 'wong']
        }
        
        for name, agents in squads.items():
            if st.button(f"Spawn {name}", use_container_width=True, key=f"sidebar_squad_{name}"):
                for agent_name in agents:
                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                st.success(f"Spawned {name}!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 🎮 Agent Management")
        
        if st.button("🤖 Full Agent Control", use_container_width=True):
            st.session_state.show_agent_page = True
            st.rerun()
        
        if st.button("➕ Create New Agent", use_container_width=True):
            st.session_state.show_create_page = True
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📋 Other Pages")
        
        if st.button("📋 Missions", use_container_width=True):
            st.info("Missions page - work in progress")
        
        if st.button("📊 Analytics", use_container_width=True):
            st.info("Analytics page - work in progress")
        
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Handle page switching
if st.session_state.get('show_agent_page'):
    del st.session_state.show_agent_page
    st.markdown("## 🤖 Agent Control")
    data = get_dashboard_data()
    if data:
        for agent in data['agents']:
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"{agent['avatar']} {agent['name']} - {agent['status']}")
            with cols[1]:
                if st.button("Respawn", key=f"respawn_{agent['id']}"):
                    st.session_state.orchestrator.kill_agent(agent['id'])
                    time.sleep(0.5)
                    result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                    st.rerun()
            with cols[2]:
                if st.button("Kill", key=f"kill_{agent['id']}"):
                    st.session_state.orchestrator.kill_agent(agent['id'])
                    resource_monitor.unregister_agent(agent['id'])
                    st.rerun()
    if st.button("← Back to Dashboard"):
        st.rerun()

if st.session_state.get('show_create_page'):
    del st.session_state.show_create_page
    st.markdown("## ➕ Create New Agent")
    
    templates = agent_factory.list_templates()
    st.markdown("### From Template")
    
    for key, label in templates.items():
        with st.expander(label):
            name = st.text_input(f"Name", key=f"create_name_{key}")
            if st.button(f"Create", key=f"create_btn_{key}"):
                if name:
                    soul_path = agent_factory.create_agent_from_template(key, name)
                    if soul_path:
                        result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                            st.success(f"Created {name}!")
                            time.sleep(1)
                            st.rerun()
    
    if st.button("← Back to Dashboard"):
        st.rerun()
