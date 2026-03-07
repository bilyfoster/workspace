#!/usr/bin/env python3
"""
Workspace Dashboard v1.6.1 - Fixed HUD with Collapse

Usage:
    streamlit run dashboard.py

Version: v1.6.1
"""
import streamlit as st
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from workspace_orchestrator import get_orchestrator
from shared.resource_monitor import resource_monitor
from shared.agent_factory import agent_factory

# Page config
st.set_page_config(
    page_title="Workspace | HUD v1.6.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS ====================
st.markdown("""
<style>
    /* HUD Container */
    .hud-container {
        background: linear-gradient(180deg, rgba(30,30,40,0.98) 0%, rgba(20,20,30,0.95) 100%);
        border-radius: 0 0 16px 16px;
        border: 1px solid rgba(255,255,255,0.1);
        border-top: none;
        padding: 12px 20px;
        margin: -6rem -4rem 0 -4rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    
    .hud-collapsed {
        padding: 8px 20px !important;
    }
    
    .hud-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    
    .hud-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #667eea;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .hud-controls {
        display: flex;
        gap: 8px;
    }
    
    .hud-btn {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        color: white;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.8rem;
        transition: all 0.2s;
    }
    
    .hud-btn:hover {
        background: rgba(255,255,255,0.2);
    }
    
    /* Metrics */
    .hud-metrics {
        display: flex;
        gap: 24px;
        margin-bottom: 12px;
    }
    
    .hud-metric {
        text-align: center;
        color: white;
    }
    
    .hud-metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .hud-metric-value.working {
        color: #ffc107;
        animation: pulse 2s infinite;
    }
    
    .hud-metric-value.alert {
        color: #ff4757;
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    .hud-metric-label {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Agent Cards */
    .hud-agents {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 4px 0;
    }
    
    .hud-agent-card {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 10px 14px;
        min-width: 120px;
        text-align: center;
        border-left: 3px solid transparent;
        transition: all 0.2s;
    }
    
    .hud-agent-card:hover {
        background: rgba(255,255,255,0.1);
        transform: translateY(-2px);
    }
    
    .hud-agent-card.idle { border-left-color: #2ed573; }
    .hud-agent-card.working { 
        border-left-color: #ffc107; 
        background: rgba(255,193,7,0.1);
    }
    .hud-agent-card.error { border-left-color: #ff4757; }
    
    .hud-agent-avatar {
        font-size: 1.4rem;
        margin-bottom: 2px;
    }
    
    .hud-agent-name {
        font-size: 0.85rem;
        font-weight: 600;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .hud-agent-status {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.6);
        margin-top: 2px;
    }
    
    .hud-agent-task {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.5);
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 110px;
    }
    
    /* Chat Area */
    .chat-container {
        padding: 20px 0;
        max-width: 800px;
        margin: 0 auto;
    }
    
    .chat-message {
        margin: 12px 0;
    }
    
    .chat-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 14px 18px;
        margin-left: auto;
        max-width: 75%;
    }
    
    .chat-agent {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 18px 18px 18px 4px;
        padding: 14px 18px;
        margin-right: auto;
        max-width: 75%;
    }
    
    .chat-header {
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 4px;
        opacity: 0.9;
    }
    
    .thinking-box {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(102,126,234,0.1);
        border: 2px solid rgba(102,126,234,0.3);
        border-radius: 20px;
        padding: 10px 18px;
        margin: 10px 0;
    }
    
    .dot {
        width: 8px;
        height: 8px;
        background: #667eea;
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    
    .dot:nth-child(2) { animation-delay: 0.16s; }
    .dot:nth-child(3) { animation-delay: 0.32s; }
    
    @keyframes bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    .welcome-box {
        text-align: center;
        padding: 60px 20px;
        color: #6c757d;
    }
    
    .welcome-title {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 16px;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = get_orchestrator()
if 'resource_monitor' not in st.session_state:
    st.session_state.resource_monitor = resource_monitor
    resource_monitor.start_monitoring(interval=5.0)
if 'agent_factory' not in st.session_state:
    st.session_state.agent_factory = agent_factory
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'hud_collapsed' not in st.session_state:
    st.session_state.hud_collapsed = False
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"
if 'thinking' not in st.session_state:
    st.session_state.thinking = False
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None

def get_data():
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def render_hud():
    """Render the HUD panel"""
    data = get_data()
    if not data:
        return
    
    agents = data['agents']
    working = len([a for a in agents if a['status'] == 'working'])
    errors = len([a for a in agents if a['status'] == 'error'])
    missions = len([m for m in data['missions'] if m['status'] == 'active'])
    tasks = sum(a['tasks_completed'] for a in agents)
    
    collapse_class = "hud-collapsed" if st.session_state.hud_collapsed else ""
    
    # Start HUD container
    st.markdown(f'<div class="hud-container {collapse_class}">', unsafe_allow_html=True)
    
    # Header with controls
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        st.markdown('<div class="hud-title">🎯 Workspace</div>', unsafe_allow_html=True)
    
    with col2:
        if not st.session_state.hud_collapsed:
            # Metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f'<div class="hud-metric"><div class="hud-metric-value">{len(agents)}</div><div class="hud-metric-label">Agents</div></div>', unsafe_allow_html=True)
            with c2:
                working_class = "working" if working > 0 else ""
                st.markdown(f'<div class="hud-metric"><div class="hud-metric-value {working_class}">{working}</div><div class="hud-metric-label">Working</div></div>', unsafe_allow_html=True)
            with c3:
                alert_class = "alert" if errors > 0 else ""
                st.markdown(f'<div class="hud-metric"><div class="hud-metric-value {alert_class}">{errors}</div><div class="hud-metric-label">Alerts</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="hud-metric"><div class="hud-metric-value">{missions}</div><div class="hud-metric-label">Missions</div></div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div class="hud-metric"><div class="hud-metric-value">{tasks}</div><div class="hud-metric-label">Tasks</div></div>', unsafe_allow_html=True)
    
    with col3:
        # Collapse/Expand button
        btn_label = "▼" if st.session_state.hud_collapsed else "▲"
        if st.button(btn_label, key="hud_toggle", help="Collapse/Expand HUD"):
            st.session_state.hud_collapsed = not st.session_state.hud_collapsed
            st.rerun()
    
    # Agent cards (only if not collapsed)
    if not st.session_state.hud_collapsed:
        st.markdown("---")
        
        if agents:
            # Display agents in a row
            cols = st.columns(min(len(agents), 8))
            for idx, agent in enumerate(agents[:8]):
                with cols[idx]:
                    status = agent['status']
                    task_preview = ""
                    if agent.get('current_task'):
                        task_preview = f"<div class='hud-agent-task'>{agent['current_task'][:20]}...</div>"
                    
                    # Make agent card clickable
                    if st.button(
                        f"{agent['avatar']}\n{agent['name']}\n{status.upper()}",
                        key=f"agent_card_{agent['id']}",
                        use_container_width=True,
                        type="secondary" if status == "idle" else "primary"
                    ):
                        st.session_state.selected_agent = agent
                        st.session_state.page = "chat"
                        st.rerun()
        else:
            st.info("No agents active. Use sidebar to spawn.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_dashboard():
    """Main dashboard with chat"""
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state.messages and not st.session_state.selected_agent:
        # Welcome message
        st.markdown("""
        <div class="welcome-box">
            <div class="welcome-title">🎩 Welcome to Workspace</div>
            <p><b>Chat with your Manager</b> to orchestrate your team</p>
            <p><small>Try: "Who's working on what?" or "Spawn the creative squad"</small></p>
            <p><small>Or click an agent card in the HUD above to chat directly</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show selected agent context
    if st.session_state.selected_agent:
        agent = st.session_state.selected_agent
        st.info(f"💬 Chatting with {agent['avatar']} {agent['name']} - Click another agent or use sidebar to change")
    
    # Display messages
    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div class="chat-message">
                <div class="chat-user">
                    <div class="chat-header">You</div>
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            avatar = msg.get('avatar', '🤖')
            name = msg.get('name', 'Agent')
            st.markdown(f"""
            <div class="chat-message">
                <div class="chat-agent">
                    <div class="chat-header">{avatar} {name}</div>
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Thinking indicator
    if st.session_state.thinking:
        st.markdown("""
        <div class="thinking-box">
            <span>🧠 Thinking</span>
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input at bottom
    st.markdown("---")
    col1, col2 = st.columns([6, 1])
    with col1:
        message = st.text_input(
            "Message",
            placeholder="Ask Manager to spawn agents, check status, or chat...",
            label_visibility="collapsed",
            key="main_input"
        )
    with col2:
        if st.button("Send 📤", use_container_width=True):
            if message:
                process_message(message)

def process_message(message: str):
    """Process user message and get response"""
    if not message.strip():
        return
    
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": message
    })
    
    st.session_state.thinking = True
    st.rerun()

def generate_response():
    """Generate agent response"""
    if not st.session_state.thinking:
        return
    
    # Get last user message
    last_msg = None
    for msg in reversed(st.session_state.messages):
        if msg['role'] == 'user':
            last_msg = msg['content']
            break
    
    if not last_msg:
        st.session_state.thinking = False
        return
    
    data = get_data()
    if not data:
        st.session_state.messages.append({
            "role": "agent",
            "name": "System",
            "avatar": "⚠️",
            "content": "Error connecting to system"
        })
        st.session_state.thinking = False
        st.rerun()
        return
    
    msg_lower = last_msg.lower()
    
    # Check if asking about a specific agent
    target_agent = None
    for agent in data['agents']:
        if agent['name'].lower() in msg_lower:
            target_agent = agent
            break
    
    # Handle commands
    if "who" in msg_lower and ("working" in msg_lower or "doing" in msg_lower):
        summary = "**Team Status:**\n\n"
        for a in data['agents']:
            status_icon = "⚡" if a['status'] == 'working' else "☕"
            task = f" - {a.get('current_task', '')[:30]}..." if a.get('current_task') else ""
            summary += f"{status_icon} **{a['name']}**: {a['status']}{task}\n"
        summary += f"\n📊 Total tasks: {sum(a['tasks_completed'] for a in data['agents'])}"
        
        st.session_state.messages.append({
            "role": "agent",
            "name": "Manager",
            "avatar": "🎩",
            "content": summary
        })
    
    elif "spawn" in msg_lower:
        spawned = []
        for name in data.get('available_agents', []):
            if name.lower() in msg_lower:
                result = st.session_state.orchestrator.spawn_agent(name)
                if result:
                    resource_monitor.register_agent(result.id, result.name)
                    spawned.append(name.title())
        
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
                "content": f"Available agents: {', '.join(data.get('available_agents', []))}"
            })
    
    elif target_agent or st.session_state.selected_agent:
        # Chat with specific agent
        agent = target_agent or st.session_state.selected_agent
        
        with st.spinner(f"{agent['name']} is thinking..."):
            response = st.session_state.orchestrator.chat_with_agent_sync(
                agent['name'], last_msg, timeout=30
            )
        
        if response:
            st.session_state.messages.append({
                "role": "agent",
                "name": agent['name'],
                "avatar": agent['avatar'],
                "content": response
            })
        else:
            st.session_state.messages.append({
                "role": "agent",
                "name": agent['name'],
                "avatar": agent['avatar'],
                "content": "❌ I'm not responding. Try respawning me from the sidebar."
            })
    
    else:
        # Default to Manager or first agent
        manager = next((a for a in data['agents'] if a['name'] == 'Manager'), None)
        target = manager or (data['agents'][0] if data['agents'] else None)
        
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
                    "role": "agent",
                    "name": "System",
                    "avatar": "⚠️",
                    "content": "No response. Agents may be offline."
                })
        else:
            st.session_state.messages.append({
                "role": "agent",
                "name": "System",
                "avatar": "🤖",
                "content": "No agents available. Use the sidebar to spawn some!"
            })
    
    st.session_state.thinking = False
    st.rerun()

def render_agent_control():
    """Agent management page"""
    st.header("🤖 Agent Control")
    
    data = get_data()
    if not data:
        return
    
    # Tabs for different functions
    tab1, tab2, tab3 = st.tabs(["Active Agents", "Spawn Agents", "Create New"])
    
    with tab1:
        if not data['agents']:
            st.info("No agents running")
        else:
            for agent in data['agents']:
                with st.expander(f"{agent['avatar']} {agent['name']} ({agent['status']})"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**Role:** {agent['role']}")
                        st.write(f"**Tasks:** {agent['tasks_completed']}")
                        if agent.get('current_task'):
                            st.write(f"**Current:** {agent['current_task']}")
                    with col2:
                        if st.button("🔄 Respawn", key=f"respawn_{agent['id']}"):
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            time.sleep(0.5)
                            result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                            if result:
                                resource_monitor.register_agent(result.id, result.name)
                            st.rerun()
                    with col3:
                        if st.button("🛑 Kill", key=f"kill_{agent['id']}"):
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            resource_monitor.unregister_agent(agent['id'])
                            st.rerun()
    
    with tab2:
        st.subheader("Available Agents")
        available = data.get('available_agents', [])
        
        cols = st.columns(4)
        for idx, name in enumerate(available):
            with cols[idx % 4]:
                is_running = any(a['name'].lower() == name.lower() for a in data['agents'])
                if is_running:
                    st.button(f"✅ {name.title()}", disabled=True, use_container_width=True)
                else:
                    if st.button(f"🚀 {name.title()}", key=f"spawn_{name}", use_container_width=True):
                        result = st.session_state.orchestrator.spawn_agent(name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                            st.success(f"Spawned {name}!")
                            time.sleep(1)
                            st.rerun()
        
        st.divider()
        st.subheader("Quick Squads")
        
        squads = {
            "🎯 Sales": ['hunter', 'pepper', 'sage'],
            "🎨 Creative": ['quill', 'pixel', 'shuri'],
            "💻 Dev": ['code', 'guardian', 'wong'],
            "🔬 Research": ['scout', 'sage', 'shuri']
        }
        
        for squad_name, agents in squads.items():
            if st.button(f"Spawn {squad_name}", key=f"squad_{squad_name}"):
                for agent_name in agents:
                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                st.success(f"Spawned {squad_name}!")
                time.sleep(1)
                st.rerun()
    
    with tab3:
        st.subheader("Create Custom Agent")
        
        templates = agent_factory.list_templates()
        
        st.markdown("**From Template:**")
        for key, label in templates.items():
            with st.expander(label):
                name = st.text_input("Name", key=f"template_name_{key}")
                if st.button("Create", key=f"template_create_{key}"):
                    if name:
                        soul_path = agent_factory.create_agent_from_template(key, name)
                        if soul_path:
                            result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                            if result:
                                resource_monitor.register_agent(result.id, result.name)
                                st.success(f"Created {name}!")
                                time.sleep(1)
                                st.rerun()
        
        st.divider()
        st.markdown("**Fully Custom:**")
        
        with st.form("custom_agent"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *")
                role = st.text_input("Role *")
                avatar = st.text_input("Avatar (emoji)", value="🤖")
            with col2:
                model = st.selectbox("Model", ["qwen3.5:9b", "dolphin3", "gemma3", "qwen3-coder"])
                temp = st.slider("Temperature", 0.0, 1.0, 0.7)
            
            essence = st.text_area("Essence/Personality *", height=100)
            skills = st.text_area("Skills (one per line) *", height=100)
            
            if st.form_submit_button("✨ Create Agent"):
                if all([name, role, essence, skills]):
                    skill_list = [s.strip() for s in skills.split('\n') if s.strip()]
                    soul_path = agent_factory.create_custom_agent(
                        name=name, role=role, avatar=avatar, essence=essence,
                        skills=skill_list, model=model, temperature=temp
                    )
                    if soul_path:
                        result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                            st.success(f"Created {name}!")
                            time.sleep(1)
                            st.rerun()

def render_missions():
    """Missions page"""
    st.header("📋 Missions")
    
    data = get_data()
    if not data:
        return
    
    missions = data.get('missions', [])
    
    if not missions:
        st.info("No missions yet")
    else:
        for mission in missions:
            with st.expander(f"{mission['title']} ({mission['progress']['percent']}%)"):
                st.write(f"Status: {mission['status']}")
                st.write(f"Tasks: {mission['progress']['completed']}/{mission['progress']['total']}")
                
                if mission['progress']['percent'] < 100:
                    if st.button("🚀 Execute", key=f"exec_{mission['id']}"):
                        st.session_state.orchestrator.execute_mission_auto(mission['id'])
                        st.success("Started!")
    
    st.divider()
    st.subheader("Create New Mission")
    
    with st.form("new_mission"):
        title = st.text_input("Title *")
        desc = st.text_area("Description")
        
        tasks = []
        for i in range(3):
            col1, col2 = st.columns([3, 2])
            with col1:
                task_desc = st.text_input(f"Task {i+1}", key=f"mission_task_{i}")
            with col2:
                agent_list = ["Auto"] + [a['name'] for a in data['agents']]
                assigned = st.selectbox(f"Assign", agent_list, key=f"mission_assign_{i}")
            if task_desc:
                tasks.append({"description": task_desc, "assigned_to": None if assigned == "Auto" else assigned})
        
        if st.form_submit_button("Create Mission"):
            if title and tasks:
                mission = st.session_state.orchestrator.create_mission(title=title, description=desc, tasks=tasks)
                st.success(f"Created: {mission.id}")
                time.sleep(1)
                st.rerun()

# ==================== MAIN APP ====================

# Process thinking state
if st.session_state.thinking:
    generate_response()

# Render HUD
render_hud()

# Sidebar Navigation
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()
    
    if st.button("🤖 Agent Control", use_container_width=True):
        st.session_state.page = "agents"
        st.rerun()
    
    if st.button("📋 Missions", use_container_width=True):
        st.session_state.page = "missions"
        st.rerun()
    
    st.markdown("---")
    
    if st.button("🚀 Spawn Manager", use_container_width=True):
        result = st.session_state.orchestrator.spawn_agent('manager')
        if result:
            resource_monitor.register_agent(result.id, result.name)
            st.success("Manager spawned!")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.selected_agent = None
        st.rerun()
    
    st.markdown("---")
    st.caption(f"Workspace v1.6.1")

# Render main content based on page
if st.session_state.page == "dashboard":
    render_dashboard()
elif st.session_state.page == "agents":
    render_agent_control()
elif st.session_state.page == "missions":
    render_missions()
elif st.session_state.page == "chat":
    # Chat with selected agent
    if st.session_state.selected_agent:
        st.info(f"Chatting with {st.session_state.selected_agent['name']}")
        render_dashboard()
    else:
        st.session_state.page = "dashboard"
        st.rerun()
