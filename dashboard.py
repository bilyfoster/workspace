#!/usr/bin/env python3
"""
Workspace Dashboard v1.5.0

Mission Control with Manager Overseer, dynamic agent creation,
and visual processing indicators.

Usage:
    streamlit run dashboard.py

Version: v1.5.0
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
from shared.bus.handoff import handoff_manager
from shared.bus.group_chat import group_chat_manager
from shared.bus.alerts import alert_manager
from shared.resource_monitor import resource_monitor
from shared.agent_factory import agent_factory, AgentFactory

# Page config
st.set_page_config(
    page_title="Workspace | Mission Control v1.5.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS WITH THINKING ANIMATIONS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Thinking/Processing Animation */
    .thinking-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 25px;
        color: white;
        font-weight: 500;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        animation: pulse-glow 2s infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); }
        50% { box-shadow: 0 4px 25px rgba(102, 126, 234, 0.7); }
    }
    
    .thinking-dots {
        display: flex;
        gap: 6px;
    }
    
    .thinking-dot {
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: thinking-bounce 1.4s infinite ease-in-out both;
    }
    
    .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
    .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
    .thinking-dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes thinking-bounce {
        0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
    
    .brain-wave {
        display: inline-block;
        animation: brain-pulse 1s infinite;
    }
    
    @keyframes brain-pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.1); opacity: 0.8; }
    }
    
    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
    }
    .status-idle {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-working {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
        animation: status-glow 2s infinite;
    }
    .status-error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
        animation: error-pulse 1s infinite;
    }
    
    @keyframes status-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255, 193, 7, 0.3); }
        50% { box-shadow: 0 0 15px rgba(255, 193, 7, 0.6); }
    }
    
    @keyframes error-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    /* Agent cards */
    .agent-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .agent-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .agent-card.working {
        border-left-color: #ffc107;
        background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
    }
    .agent-card.error {
        border-left-color: #dc3545;
        background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
    }
    
    /* Resource bars */
    .resource-bar {
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
        margin: 4px 0;
    }
    .resource-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s;
    }
    .resource-bar-fill.low { background: #28a745; }
    .resource-bar-fill.medium { background: #ffc107; }
    .resource-bar-fill.high { background: #dc3545; }
    
    /* Chat bubbles */
    .chat-message-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px 15px 0 15px;
        padding: 12px 16px;
        margin: 8px 0 8px auto;
        max-width: 80%;
        float: right;
        clear: both;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .chat-message-agent {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 15px 15px 15px 0;
        padding: 12px 16px;
        margin: 8px auto 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Activity timeline */
    .activity-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        font-size: 0.9em;
        border-left: 3px solid transparent;
    }
    .activity-task-started { background: #e3f2fd; border-left-color: #2196f3; }
    .activity-task-completed { background: #e8f5e9; border-left-color: #4caf50; }
    .activity-agent-online { background: #f3e5f5; border-left-color: #9c27b0; }
    .activity-agent-offline { background: #fafafa; border-left-color: #9e9e9e; }
    .activity-error { background: #ffebee; border-left-color: #f44336; }
    
    /* Manager overview cards */
    .overview-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card h2 {
        margin: 0;
        font-size: 2.5rem;
    }
    .metric-card p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
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
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}
if 'thinking_agents' not in st.session_state:
    st.session_state.thinking_agents = set()  # Track which agents are thinking

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def render_thinking_indicator(agent_name: str, message: str = "Processing..."):
    """Render a thinking/processing animation"""
    st.markdown(f"""
    <div class="thinking-container">
        <span class="brain-wave">🧠</span>
        <span>{agent_name} is {message}</span>
        <div class="thinking-dots">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_status_badge(status: str, agent_name: str = "") -> str:
    """Render a status badge with appropriate styling"""
    badges = {
        'idle': ('☕', 'Idle'),
        'working': ('⚡', 'Working'),
        'error': ('⚠️', 'Error'),
        'offline': ('💤', 'Offline'),
        'initializing': ('🔄', 'Starting...')
    }
    icon, text = badges.get(status, ('⚪', status))
    
    if status == 'working':
        return f'<span class="status-badge status-working">{icon} {text}</span>'
    elif status == 'error':
        return f'<span class="status-badge status-error">{icon} {text}</span>'
    else:
        return f'<span class="status-badge status-idle">{icon} {text}</span>'

def render_resource_bar(value: float, label: str):
    """Render a resource usage bar"""
    pct = min(100, max(0, value))
    css_class = 'low' if pct < 50 else 'medium' if pct < 80 else 'high'
    st.markdown(f"""
    <div style="margin: 8px 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
            <span>{label}</span>
            <span>{pct:.1f}%</span>
        </div>
        <div class="resource-bar">
            <div class="resource-bar-fill {css_class}" style="width: {pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
st.sidebar.markdown("# 🎯 Workspace")
st.sidebar.markdown("### Mission Control v1.5.0")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["🎩 Manager", "🏠 Dashboard", "💬 Chat", "🤖 Agents", "📋 Missions", 
     "📊 Analytics", "📜 Logs", "⚙️ System"]
)

# ==================== MANAGER PAGE (PRIMARY) ====================
if page == "🎩 Manager":
    st.markdown('<p class="main-header">🎩 Manager Overview</p>', unsafe_allow_html=True)
    st.markdown("Your central command center for the entire Workspace.")
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Spawn Manager if not running
    manager_running = any(a['name'] == 'Manager' for a in data['agents'])
    if not manager_running:
        st.info("🎩 Manager agent is not active. Spawn the Manager to have an overseer.")
        if st.button("🚀 Spawn Manager", type="primary"):
            with st.spinner("Spawning Manager..."):
                result = st.session_state.orchestrator.spawn_agent('manager')
                if result:
                    resource_monitor.register_agent(result.id, result.name)
                    st.success("✅ Manager is online!")
                    time.sleep(1)
                    st.rerun()
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{len(data['agents'])}</h2>
            <p>🤖 Agents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        working = len([a for a in data['agents'] if a['status'] == 'working'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{working}</h2>
            <p>⚡ Working</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        active_missions = len([m for m in data['missions'] if m['status'] == 'active'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{active_missions}</h2>
            <p>🚀 Missions</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        completed_tasks = sum(a['tasks_completed'] for a in data['agents'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{completed_tasks}</h2>
            <p>✅ Tasks Done</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        sys_res = resource_monitor.get_system_summary()
        mem_pct = sys_res.get('system_memory_percent', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h2>{mem_pct:.0f}%</h2>
            <p>💾 Memory</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Main manager interface
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Live Status", "💬 Chat with Manager", "➕ Create Agent", "🎯 Quick Actions"])
    
    with tab1:
        st.subheader("Live Team Status")
        
        if not data['agents']:
            st.info("No agents running. Use '➕ Create Agent' or '🤖 Agents' to spawn your team.")
        else:
            # Show agents in a detailed table
            for agent in data['agents']:
                card_class = "working" if agent['status'] == 'working' else "error" if agent['status'] == 'error' else ""
                
                with st.container():
                    cols = st.columns([2, 2, 2, 2, 3])
                    
                    with cols[0]:
                        st.markdown(f"""
                        <div class="agent-card {card_class}">
                            <h3>{agent['avatar']} {agent['name']}</h3>
                            <p>{render_status_badge(agent['status'], agent['name'])}</p>
                            <p style="font-size: 0.85em; color: #666;">{agent['role']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with cols[1]:
                        st.markdown("**📊 Resources**")
                        resources = resource_monitor.get_agent_resources(agent['id'])
                        if resources and resources.get_current():
                            snap = resources.get_current()
                            st.text(f"CPU: {snap.cpu_percent:.1f}%")
                            st.text(f"Memory: {snap.memory_mb:.1f} MB")
                        else:
                            st.text("Collecting...")
                    
                    with cols[2]:
                        st.markdown("**✅ Activity**")
                        st.text(f"Tasks: {agent['tasks_completed']}")
                        if agent.get('current_task'):
                            st.text(f"Now: {agent['current_task'][:25]}...")
                    
                    with cols[3]:
                        st.markdown("**🎮 Actions**")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("💬", key=f"mgr_chat_{agent['id']}"):
                                st.session_state.selected_agent_chat = agent['id']
                                st.rerun()
                        with c2:
                            if st.button("🔧", key=f"mgr_manage_{agent['id']}"):
                                st.session_state.selected_page = "🤖 Agents"
                                st.rerun()
                    
                    with cols[4]:
                        # Show thinking indicator if working
                        if agent['status'] == 'working':
                            render_thinking_indicator(agent['name'], f"working on: {agent.get('current_task', 'task')[:30]}...")
    
    with tab2:
        st.subheader("💬 Chat with Manager")
        
        manager_agent = next((a for a in data['agents'] if a['name'] == 'Manager'), None)
        
        if not manager_agent:
            st.warning("🎩 Manager agent is not active. Spawn the Manager first!")
        else:
            # Initialize chat history for Manager
            if 'manager_chat' not in st.session_state:
                st.session_state.manager_chat = []
            
            # Display chat
            chat_container = st.container()
            with chat_container:
                if not st.session_state.manager_chat:
                    st.info("👋 Ask the Manager anything!\n\nTry:\n• 'Who's working on what?'\n• 'Spawn the creative squad'\n• 'Create a data analyst agent named Atlas'")
                else:
                    for msg in st.session_state.manager_chat:
                        if msg['role'] == 'user':
                            st.markdown(f"""
                            <div class="chat-message-user">
                                <b>You:</b><br>{msg['content']}
                            </div>
                            <div style="clear: both;"></div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="chat-message-agent">
                                <b>🎩 Manager:</b><br>{msg['content']}
                            </div>
                            <div style="clear: both;"></div>
                            """, unsafe_allow_html=True)
            
            # Input
            with st.form("manager_chat_form", clear_on_submit=True):
                msg = st.text_input("Message Manager", placeholder="Ask about team status, spawn agents, create new ones...")
                cols = st.columns([1, 1])
                with cols[0]:
                    submitted = st.form_submit_button("Send 📤", use_container_width=True)
                with cols[1]:
                    if st.form_submit_button("🧹 Clear", use_container_width=True):
                        st.session_state.manager_chat = []
                        st.rerun()
                
                if submitted and msg:
                    st.session_state.manager_chat.append({"role": "user", "content": msg})
                    
                    # Check for special commands
                    msg_lower = msg.lower()
                    
                    if "who" in msg_lower and ("working" in msg_lower or "doing" in msg_lower):
                        # Generate status summary
                        summary = "Here's what everyone's doing:\n\n"
                        for a in data['agents']:
                            status = "working on: " + a.get('current_task', 'something')[:40] if a['status'] == 'working' else a['status']
                            summary += f"• {a['avatar']} **{a['name']}** - {status}\n"
                        summary += f"\n📊 Total tasks completed: {sum(a['tasks_completed'] for a in data['agents'])}"
                        st.session_state.manager_chat.append({"role": "agent", "content": summary})
                        st.rerun()
                    
                    elif "spawn" in msg_lower or "start" in msg_lower:
                        # Extract agent names
                        spawned = []
                        for agent_name in data.get('available_agents', []):
                            if agent_name.lower() in msg_lower:
                                result = st.session_state.orchestrator.spawn_agent(agent_name)
                                if result:
                                    resource_monitor.register_agent(result.id, result.name)
                                    spawned.append(agent_name.title())
                        
                        if spawned:
                            st.session_state.manager_chat.append({"role": "agent", "content": f"✅ Spawned: {', '.join(spawned)}"})
                        else:
                            # Show thinking and then respond
                            st.session_state.thinking_agents.add('manager')
                            with st.spinner("🧠 Manager is thinking..."):
                                response = st.session_state.orchestrator.chat_with_agent_sync('Manager', msg, timeout=30)
                            st.session_state.thinking_agents.discard('manager')
                            if response:
                                st.session_state.manager_chat.append({"role": "agent", "content": response})
                        st.rerun()
                    
                    else:
                        # Regular chat with thinking animation
                        st.session_state.thinking_agents.add('manager')
                        with st.spinner("🧠 Manager is thinking..."):
                            response = st.session_state.orchestrator.chat_with_agent_sync('Manager', msg, timeout=30)
                        st.session_state.thinking_agents.discard('manager')
                        
                        if response:
                            st.session_state.manager_chat.append({"role": "agent", "content": response})
                        else:
                            st.session_state.manager_chat.append({"role": "agent", "content": "❌ I didn't get a response. I may be overloaded or having issues."})
                        st.rerun()
    
    with tab3:
        st.subheader("➕ Create New Agent")
        st.markdown("Need a specialist that doesn't exist? Create one!")
        
        create_tab1, create_tab2 = st.tabs(["📋 From Template", "✨ Custom"])
        
        with create_tab1:
            templates = agent_factory.list_templates()
            
            st.markdown("**Choose a template:**")
            
            cols = st.columns(3)
            for idx, (key, label) in enumerate(templates.items()):
                with cols[idx % 3]:
                    with st.expander(f"{label}"):
                        template = agent_factory.TEMPLATES[key]
                        st.write(f"**Model:** {template.model}")
                        st.write(f"**Skills:** {', '.join(template.skills[:3])}...")
                        
                        name = st.text_input(f"Name for {key}", key=f"template_name_{key}", placeholder=f"e.g., {template.role.split()[0]}")
                        if st.button(f"🚀 Create {key.replace('_', ' ').title()}", key=f"create_{key}"):
                            if name:
                                if agent_factory.agent_exists(name):
                                    st.error(f"❌ An agent named '{name}' already exists")
                                else:
                                    with st.spinner(f"Creating {name}..."):
                                        soul_path = agent_factory.create_agent_from_template(key, name)
                                        if soul_path:
                                            # Auto-spawn
                                            result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                                            if result:
                                                resource_monitor.register_agent(result.id, result.name)
                                                st.success(f"✅ Created and spawned {name}!")
                                                time.sleep(1)
                                                st.rerun()
                                        else:
                                            st.error("❌ Failed to create agent")
        
        with create_tab2:
            st.markdown("**Create a completely custom agent:**")
            
            with st.form("custom_agent_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Agent Name *", placeholder="e.g., Atlas")
                    role = st.text_input("Role/Title *", placeholder="e.g., Data Visualization Specialist")
                    avatar = st.text_input("Avatar (emoji) *", value="🤖")
                with col2:
                    model = st.selectbox("Model", ["qwen3.5:9b", "dolphin3", "gemma3", "qwen3-coder"])
                    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
                
                essence = st.text_area("Essence/Personality *", 
                    placeholder="Describe who this agent is and how they approach their work...")
                
                skills_text = st.text_area("Skills (one per line) *",
                    placeholder="e.g.,\nData visualization\nPython programming\nStatistical analysis")
                
                submitted = st.form_submit_button("✨ Create Custom Agent", type="primary")
                
                if submitted:
                    if not all([name, role, essence, skills_text]):
                        st.error("Please fill in all required fields")
                    elif agent_factory.agent_exists(name):
                        st.error(f"An agent named '{name}' already exists")
                    else:
                        skills = [s.strip() for s in skills_text.split('\n') if s.strip()]
                        with st.spinner(f"Creating {name}..."):
                            soul_path = agent_factory.create_custom_agent(
                                name=name, role=role, avatar=avatar, essence=essence,
                                skills=skills, model=model, temperature=temperature
                            )
                            if soul_path:
                                # Auto-spawn
                                result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                                if result:
                                    resource_monitor.register_agent(result.id, result.name)
                                    st.success(f"✅ Created and spawned {name}!")
                                    st.info(f"📁 Soul file: {soul_path}")
                                    time.sleep(2)
                                    st.rerun()
                            else:
                                st.error("❌ Failed to create agent")
    
    with tab4:
        st.subheader("🎯 Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**⚡ Spawn Squads**")
            squads = {
                "🎯 Sales": ['hunter', 'pepper', 'sage'],
                "🎨 Creative": ['quill', 'pixel', 'shuri'],
                "💻 Dev": ['code', 'guardian', 'wong'],
                "🔬 Research": ['scout', 'sage', 'shuri']
            }
            for name, agents in squads.items():
                if st.button(f"Spawn {name}", key=f"squad_{name}"):
                    for agent_name in agents:
                        result = st.session_state.orchestrator.spawn_agent(agent_name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                    st.success(f"✅ Spawned {name} squad!")
                    time.sleep(1)
                    st.rerun()
        
        with col2:
            st.markdown("**🔄 Global Actions**")
            if st.button("Respawn All", key="respawn_all"):
                names = [a['name'].lower() for a in data['agents']]
                for agent in data['agents']:
                    st.session_state.orchestrator.kill_agent(agent['id'])
                time.sleep(0.5)
                for name in names:
                    result = st.session_state.orchestrator.spawn_agent(name)
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                st.success("✅ All agents respawned!")
                time.sleep(1)
                st.rerun()
            
            if st.button("Kill All", key="kill_all"):
                for agent in data['agents']:
                    st.session_state.orchestrator.kill_agent(agent['id'])
                    resource_monitor.unregister_agent(agent['id'])
                st.warning("🛑 All agents stopped")
                time.sleep(1)
                st.rerun()
        
        with col3:
            st.markdown("**📊 System**")
            if st.button("🔄 Refresh Data"):
                st.rerun()
            
            sys_res = resource_monitor.get_system_summary()
            st.text(f"Agents: {sys_res.get('total_agents', 0)}")
            st.text(f"Memory: {sys_res.get('system_memory_percent', 0):.1f}%")
            st.text(f"CPU: {sys_res.get('system_cpu_percent', 0):.1f}%")

# ==================== OTHER PAGES ====================
# (Dashboard, Chat, Agents, Missions, Analytics, Logs, System pages...)

elif page == "🏠 Dashboard":
    st.markdown('<p class="main-header">🏠 Dashboard</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if data:
        st.json({"agents": len(data['agents']), "missions": len(data['missions'])})

elif page == "💬 Chat":
    st.markdown('<p class="main-header">💬 Chat with Agents</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if not data or not data['agents']:
        st.warning("No agents available!")
        st.stop()
    
    # Agent selector
    agent_options = {a['id']: f"{a['avatar']} {a['name']}" for a in data['agents']}
    selected_id = st.selectbox("Select Agent", options=list(agent_options.keys()), 
                              format_func=lambda x: agent_options[x])
    selected_agent = next((a for a in data['agents'] if a['id'] == selected_id), None)
    
    if selected_agent:
        st.subheader(f"Chat with {selected_agent['name']}")
        
        # Initialize chat history
        if selected_id not in st.session_state.chat_history:
            st.session_state.chat_history[selected_id] = []
        
        # Show thinking indicator at top if working
        if selected_agent['status'] == 'working':
            render_thinking_indicator(selected_agent['name'], 
                f"working on: {selected_agent.get('current_task', 'task')[:40]}...")
        
        # Display chat
        for msg in st.session_state.chat_history[selected_id]:
            if msg['role'] == 'user':
                st.markdown(f"<div class='chat-message-user'><b>You:</b><br>{msg['content']}</div><div style='clear:both'></div>", 
                          unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-message-agent'><b>{selected_agent['name']}:</b><br>{msg['content']}</div><div style='clear:both'></div>", 
                          unsafe_allow_html=True)
        
        # Input
        with st.form("chat_form", clear_on_submit=True):
            message = st.text_input("Your message")
            submitted = st.form_submit_button("Send 📤")
            
            if submitted and message:
                st.session_state.chat_history[selected_id].append({"role": "user", "content": message})
                
                # Show thinking animation
                st.session_state.thinking_agents.add(selected_agent['name'])
                
                with st.spinner(f"🧠 {selected_agent['name']} is thinking..."):
                    # Add animated dots during thinking
                    response = st.session_state.orchestrator.chat_with_agent_sync(
                        selected_agent['name'], message, timeout=30
                    )
                
                st.session_state.thinking_agents.discard(selected_agent['name'])
                
                if response:
                    st.session_state.chat_history[selected_id].append({"role": "agent", "content": response})
                else:
                    st.error("❌ No response - agent may be stuck")
                st.rerun()

elif page == "🤖 Agents":
    st.markdown('<p class="main-header">🤖 Agent Control</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if data:
        for agent in data['agents']:
            with st.expander(f"{agent['avatar']} {agent['name']} - {agent['status']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Role:** {agent['role']}")
                    st.write(f"**Tasks:** {agent['tasks_completed']}")
                with col2:
                    if st.button("🔄 Respawn", key=f"respawn_{agent['id']}"):
                        st.session_state.orchestrator.kill_agent(agent['id'])
                        time.sleep(0.5)
                        result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                            st.success(f"{agent['name']} respawned!")
                            time.sleep(1)
                            st.rerun()
                with col3:
                    if st.button("🛑 Kill", key=f"kill_{agent['id']}"):
                        st.session_state.orchestrator.kill_agent(agent['id'])
                        resource_monitor.unregister_agent(agent['id'])
                        st.warning(f"{agent['name']} killed")
                        time.sleep(1)
                        st.rerun()

elif page == "📋 Missions":
    st.markdown('<p class="main-header">📋 Missions</p>', unsafe_allow_html=True)
    st.info("Use the Manager (🎩 Manager page) to create and manage missions with full visibility!")

elif page == "📊 Analytics":
    st.markdown('<p class="main-header">📊 Analytics</p>', unsafe_allow_html=True)
    st.info("Analytics visualization coming soon. Check the Manager page for live status!")

elif page == "📜 Logs":
    st.markdown('<p class="main-header">📜 Logs</p>', unsafe_allow_html=True)
    events = tracker.get_recent_events(50)
    for event in events[:20]:
        ts = event['timestamp'].split('T')[1][:8] if 'T' in event['timestamp'] else ''
        st.text(f"[{ts}] {event['type']}: {event['from_agent']}")

elif page == "⚙️ System":
    st.markdown('<p class="main-header">⚙️ System</p>', unsafe_allow_html=True)
    st.write("**Workspace v1.5.0**")
    st.write("Features: Manager Overseer, Dynamic Agent Creation, Resource Monitoring")

# Footer
st.sidebar.divider()
st.sidebar.markdown(f"**Workspace v1.5.0** 🎩")
st.sidebar.markdown(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
