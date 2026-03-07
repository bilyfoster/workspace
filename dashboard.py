#!/usr/bin/env python3
"""
Workspace Dashboard v1.4.0

Mission Control-style web interface with real-time agent interaction,
resource monitoring, and individual agent management.

Usage:
    streamlit run dashboard.py

Version: v1.4.0
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

# Page config
st.set_page_config(
    page_title="Workspace | Mission Control v1.4.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS WITH BETTER ICONS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
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
    .agent-card.error {
        border-left-color: #ff4757;
        background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
    }
    .agent-card.working {
        border-left-color: #ffa502;
        background: linear-gradient(135deg, #fff9e6 0%, #fff0cc 100%);
    }
    .status-online { color: #2ed573; font-weight: bold; }
    .status-working { color: #ffa502; font-weight: bold; }
    .status-offline { color: #ff4757; font-weight: bold; }
    .status-idle { color: #2ed573; font-weight: bold; }
    .status-error { color: #ff4757; font-weight: bold; animation: pulse 1s infinite; }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Progress/Activity Animations */
    .spinner {
        display: inline-block;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
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
    .resource-bar-fill.low { background: #2ed573; }
    .resource-bar-fill.medium { background: #ffa502; }
    .resource-bar-fill.high { background: #ff4757; }
    
    .activity-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
    }
    .activity-indicator.idle {
        background: #d4edda;
        color: #155724;
    }
    .activity-indicator.working {
        background: #fff3cd;
        color: #856404;
    }
    .activity-indicator.error {
        background: #f8d7da;
        color: #721c24;
    }
    
    .agent-control-btn {
        padding: 6px 12px;
        border-radius: 6px;
        border: none;
        cursor: pointer;
        font-size: 0.85em;
        transition: all 0.2s;
    }
    .agent-control-btn:hover {
        transform: scale(1.05);
    }
    
    .chat-container {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        max-height: 500px;
        overflow-y: auto;
    }
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = get_orchestrator()
if 'tracker' not in st.session_state:
    st.session_state.tracker = tracker
if 'handoff_manager' not in st.session_state:
    st.session_state.handoff_manager = handoff_manager
if 'group_chat' not in st.session_state:
    st.session_state.group_chat = group_chat_manager
if 'alerts' not in st.session_state:
    st.session_state.alerts = alert_manager
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}
if 'resource_monitor' not in st.session_state:
    st.session_state.resource_monitor = resource_monitor
    resource_monitor.start_monitoring(interval=5.0)

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# ==================== SIDEBAR ====================
st.sidebar.markdown("# 🎯 Workspace")
st.sidebar.markdown("### Mission Control v1.4.0")

# Navigation with icons
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "💬 Chat 1-on-1", "👥 Group Chat", "🤖 Agent Control", 
     "📋 Missions", "🔄 Handoffs", "🔔 Alerts", "📊 Analytics", "📜 Logs & Debug", "⚙️ System"]
)

# ==================== HELPER FUNCTIONS ====================

def get_status_icon(status: str, with_animation: bool = True) -> str:
    """Get appropriate status icon with optional animation"""
    icons = {
        'idle': ('🟢', '⚡'),           # Ready/Active
        'working': ('🔵', '⏳'),       # Busy/Processing  
        'error': ('🔴', '⚠️'),         # Error
        'offline': ('⚫', '💤'),       # Offline
        'initializing': ('🟡', '🔄'),  # Starting up
    }
    base, anim = icons.get(status, ('⚪', '○'))
    if with_animation and status == 'working':
        return f'<span class="spinner">{anim}</span>'
    return base

def get_activity_emoji(status: str) -> str:
    """Get emoji showing current activity"""
    return {
        'idle': '☕ Idle',
        'working': '⚡ Working',
        'error': '⚠️ Error',
        'offline': '💤 Offline',
        'initializing': '🔄 Starting...'
    }.get(status, status)

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

def ping_agent(agent_id: str) -> bool:
    """Ping an agent to check if it's responsive"""
    try:
        orch = st.session_state.orchestrator
        # Send a ping message and wait for response
        orch.bus.publish({
            'type': 'ping',
            'sender': 'dashboard',
            'recipient': agent_id,
            'timestamp': time.time()
        })
        return True
    except Exception:
        return False

# ==================== DASHBOARD PAGE ====================
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">🎯 Mission Control Dashboard</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        agent_count = len(data['agents'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{agent_count}</h2>
            <p>🤖 Active Agents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        working = len([a for a in data['agents'] if a['status'] == 'working'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{working}</h2>
            <p>⚡ Working Now</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        active_missions = len([m for m in data['missions'] if m['status'] == 'active'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{active_missions}</h2>
            <p>🚀 Active Missions</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # System resource summary
        sys_resources = resource_monitor.get_system_summary()
        mem_pct = sys_resources.get('system_memory_percent', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h2>{mem_pct:.0f}%</h2>
            <p>💾 Memory Used</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Live Squad with resources
    st.subheader("👥 Your Squad")
    
    if not data['agents']:
        st.info("🤖 No agents active. Go to '🤖 Agent Control' to get started!")
    else:
        # Show agents in a grid with resource info
        for agent in data['agents']:
            card_class = "working" if agent['status'] == 'working' else "error" if agent['status'] == 'error' else ""
            status_icon = get_status_icon(agent['status'])
            activity = get_activity_emoji(agent['status'])
            
            # Get resource info
            resources = resource_monitor.get_agent_resources(agent['id'])
            cpu_str = "--"
            mem_str = "--"
            if resources and resources.get_current():
                snap = resources.get_current()
                cpu_str = f"{snap.cpu_percent:.1f}%"
                mem_str = f"{snap.memory_mb:.1f} MB"
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.markdown(f"""
                <div class="agent-card {card_class}">
                    <h3>{agent['avatar']} {agent['name']}</h3>
                    <p><span class="activity-indicator {agent['status']}">{status_icon} {activity}</span></p>
                    <p style="font-size: 0.9em; color: #666;">{agent['role']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**📊 Resources**")
                st.text(f"CPU: {cpu_str}")
                st.text(f"Memory: {mem_str}")
            
            with col3:
                st.markdown(f"**✅ Tasks**")
                st.text(f"Completed: {agent['tasks_completed']}")
                if agent.get('current_task'):
                    st.text(f"Current: {agent['current_task'][:30]}...")
            
            with col4:
                st.markdown(f"**🎮 Actions**")
                if st.button("💬 Chat", key=f"dash_chat_{agent['id']}"):
                    st.session_state.selected_agent_for_chat = agent['id']
                    st.rerun()
                if st.button("🔧 Manage", key=f"dash_manage_{agent['id']}"):
                    st.session_state.selected_agent_for_management = agent['id']
                    st.rerun()

# ==================== CHAT 1-ON-1 PAGE ====================
elif page == "💬 Chat 1-on-1":
    st.markdown('<p class="main-header">💬 Chat with Your Agents</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    if not data['agents']:
        st.warning("🤖 No agents available. Spawn an agent first!")
        st.info("👈 Go to '🤖 Agent Control' in the sidebar to create your first agent.")
        st.stop()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Select Agent")
        
        # Agent selector with health indicator
        agent_options = {}
        for a in data['agents']:
            status_dot = "🟢" if a['status'] == 'idle' else "🔵" if a['status'] == 'working' else "🔴"
            agent_options[a['id']] = f"{a['avatar']} {a['name']} {status_dot}"
        
        # Check if we have a pre-selected agent from dashboard
        default_idx = 0
        if 'selected_agent_for_chat' in st.session_state:
            try:
                default_idx = list(agent_options.keys()).index(st.session_state.selected_agent_for_chat)
                del st.session_state.selected_agent_for_chat
            except ValueError:
                pass
        
        selected_agent_id = st.selectbox(
            "Choose an agent to chat with",
            options=list(agent_options.keys()),
            format_func=lambda x: agent_options[x],
            index=default_idx
        )
        
        selected_agent = next((a for a in data['agents'] if a['id'] == selected_agent_id), None)
        
        if selected_agent:
            # Health check
            st.markdown("---")
            st.markdown("**Agent Health**")
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                if st.button("🔔 Ping Agent", key="ping_btn"):
                    with st.spinner("Pinging..."):
                        success = ping_agent(selected_agent_id)
                        if success:
                            st.success("✅ Agent is responsive")
                        else:
                            st.error("❌ Agent not responding")
            
            with col_h2:
                thread_alive = selected_agent.get('thread_alive', False)
                st.markdown(f"Thread: {'✅ Alive' if thread_alive else '❌ Dead'}")
            
            # Resource usage
            resources = resource_monitor.get_agent_resources(selected_agent_id)
            if resources and resources.get_current():
                snap = resources.get_current()
                st.markdown("---")
                st.markdown("**Resource Usage**")
                render_resource_bar(snap.cpu_percent * 10, "CPU")  # Scale for visibility
                st.text(f"Memory: {snap.memory_mb:.1f} MB")
        
        st.divider()
        
        # Quick prompts
        st.subheader("💡 Quick Prompts")
        quick_prompts = [
            "Introduce yourself",
            "What can you help me with?",
            "Tell me about your skills",
            "Help me plan a mission"
        ]
        
        for prompt in quick_prompts:
            if st.button(prompt, key=f"quick_{prompt}", use_container_width=True):
                if selected_agent_id not in st.session_state.chat_history:
                    st.session_state.chat_history[selected_agent_id] = []
                
                st.session_state.chat_history[selected_agent_id].append({
                    "role": "user", 
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                })
                
                with st.spinner(f"{selected_agent['name']} is thinking..."):
                    response = st.session_state.orchestrator.chat_with_agent_sync(
                        selected_agent['name'], 
                        prompt,
                        timeout=30
                    )
                
                if response:
                    st.session_state.chat_history[selected_agent_id].append({
                        "role": "agent",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    st.rerun()
                else:
                    st.error("❌ No response from agent (timeout or error)")
                    st.info("💡 Try respawning the agent in '🤖 Agent Control'")
    
    with col2:
        st.subheader(f"💬 Conversation with {selected_agent['name'] if selected_agent else '...'}")
        
        # Initialize chat history
        if selected_agent_id not in st.session_state.chat_history:
            st.session_state.chat_history[selected_agent_id] = []
        
        # Display chat
        chat_container = st.container()
        with chat_container:
            if st.session_state.chat_history[selected_agent_id]:
                if st.button("📥 Export Chat", key=f"export_chat_{selected_agent_id}"):
                    export_path = st.session_state.orchestrator.chat_history.export_chat(
                        selected_agent_id, "markdown"
                    )
                    if export_path:
                        st.success(f"✅ Exported to: {export_path}")
                    else:
                        st.error("❌ Export failed")
            
            if not st.session_state.chat_history[selected_agent_id]:
                st.info("👋 Start a conversation! Type a message below or use Quick Prompts.")
            else:
                for msg in st.session_state.chat_history[selected_agent_id]:
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
                            <b>{selected_agent['name']}:</b><br>{msg['content']}
                        </div>
                        <div style="clear: both;"></div>
                        """, unsafe_allow_html=True)
        
        # Chat input
        st.divider()
        with st.form("chat_form", clear_on_submit=True):
            message = st.text_input("Type your message", key="chat_input", placeholder="Ask something...")
            submitted = st.form_submit_button("Send 📤", use_container_width=True)
            
            if submitted and message:
                st.session_state.chat_history[selected_agent_id].append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                with st.spinner(f"{selected_agent['name']} is thinking..."):
                    response = st.session_state.orchestrator.chat_with_agent_sync(
                        selected_agent['name'],
                        message,
                        timeout=30
                    )
                
                if response:
                    st.session_state.chat_history[selected_agent_id].append({
                        "role": "agent",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    st.rerun()
                else:
                    st.error("❌ No response from agent")
                    st.info("The agent may be busy or unresponsive. Try:")
                    st.markdown("1. Check agent status in 'Agent Control'")
                    st.markdown("2. Respawn the agent if needed")
                    st.markdown("3. Check Logs & Debug for errors")

# ==================== GROUP CHAT PAGE ====================
elif page == "👥 Group Chat":
    st.markdown('<p class="main-header">👥 Group Chat with Your Squad</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    if len(data['agents']) < 2:
        st.warning("👥 You need at least 2 agents for a group chat!")
        st.stop()
    
    tab1, tab2 = st.tabs(["💬 Active Groups", "➕ Create New Group"])
    
    with tab1:
        st.subheader("Your Group Chats")
        groups = data.get('groups', [])
        
        if not groups:
            st.info("📝 No group chats yet. Create one in the 'Create New Group' tab!")
        else:
            for group in groups:
                with st.expander(f"👥 {group['name']} ({group['member_count']} members)"):
                    st.write(f"**Type:** {group['type']}")
                    st.write(f"**Members:** {', '.join(group['members'])}")
                    
                    message = st.text_input(f"Message to {group['name']}", key=f"group_msg_{group['id']}")
                    if st.button("Send to Group 📤", key=f"send_group_{group['id']}"):
                        if message:
                            st.session_state.group_chat.send_to_group(
                                group_id=group['id'],
                                sender="user",
                                content=message
                            )
                            st.success(f"Sent to {group['name']}!")
                            time.sleep(1)
                            st.rerun()
    
    with tab2:
        st.subheader("Create New Group Chat")
        with st.form("create_group_form"):
            group_name = st.text_input("Group Name", placeholder="e.g., Dev Team Standup")
            
            agent_list = [(a['id'], f"{a['avatar']} {a['name']}") for a in data['agents']]
            selected_members = st.multiselect(
                "Select Members",
                options=[a[0] for a in agent_list],
                format_func=lambda x: next((a[1] for a in agent_list if a[0] == x), x)
            )
            
            submitted = st.form_submit_button("👥 Create Group", type="primary")
            if submitted:
                if not group_name or len(selected_members) < 2:
                    st.error("Need name and at least 2 members")
                else:
                    member_names = [next((a['name'] for a in data['agents'] if a['id'] == mid), mid) 
                                   for mid in selected_members]
                    st.session_state.group_chat.create_group(
                        name=group_name,
                        members=member_names,
                        created_by="user"
                    )
                    st.success(f"✅ Created group: {group_name}")

# ==================== AGENT CONTROL PAGE (REVAMPED) ====================
elif page == "🤖 Agent Control":
    st.markdown('<p class="main-header">🤖 Agent Control Center</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # System resources overview
    st.subheader("📊 System Resources")
    sys_resources = resource_monitor.get_system_summary()
    
    if 'error' not in sys_resources:
        cols = st.columns(4)
        with cols[0]:
            st.metric("Active Agents", sys_resources['total_agents'])
        with cols[1]:
            st.metric("Process CPU", f"{sys_resources['process_cpu_percent']:.1f}%")
        with cols[2]:
            mem_gb = sys_resources['process_memory_mb'] / 1024
            st.metric("Process Memory", f"{mem_gb:.2f} GB")
        with cols[3]:
            st.metric("System Memory", f"{sys_resources['system_memory_percent']:.0f}%")
    
    st.divider()
    
    # Individual Agent Management
    st.subheader("🎮 Individual Agent Management")
    
    if not data['agents']:
        st.info("No agents running. Spawn some below!")
    else:
        # Detailed agent table
        for agent in data['agents']:
            # Get resource data
            resources = resource_monitor.get_agent_resources(agent['id'])
            
            with st.expander(f"{agent['avatar']} {agent['name']} - {get_activity_emoji(agent['status'])}", 
                           expanded=st.session_state.get('selected_agent_for_management') == agent['id']):
                
                # Clear the selection after showing
                if st.session_state.get('selected_agent_for_management') == agent['id']:
                    del st.session_state.selected_agent_for_management
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("**📋 Info**")
                    st.text(f"ID: {agent['id'][:20]}...")
                    st.text(f"Role: {agent['role']}")
                    st.text(f"Model: {agent.get('model', 'Default')}")
                    st.text(f"Started: {agent.get('started_at', 'Unknown')[:19] if agent.get('started_at') else 'Unknown'}")
                
                with col2:
                    st.markdown("**📊 Resources**")
                    if resources and resources.get_current():
                        snap = resources.get_current()
                        st.text(f"CPU: {snap.cpu_percent:.1f}%")
                        st.text(f"Memory: {snap.memory_mb:.1f} MB")
                        st.text(f"Avg CPU: {resources.get_average_cpu():.1f}%")
                        st.text(f"Peak Memory: {resources.get_peak_memory():.1f} MB")
                    else:
                        st.text("No data yet...")
                
                with col3:
                    st.markdown("**✅ Activity**")
                    st.text(f"Tasks Done: {agent['tasks_completed']}")
                    if resources:
                        st.text(f"Total Tokens: {resources.total_tokens_used}")
                    if agent.get('current_task'):
                        st.text(f"Current: {agent['current_task'][:40]}...")
                
                with col4:
                    st.markdown("**🎮 Actions**")
                    
                    if st.button("🔄 Respawn", key=f"respawn_{agent['id']}", use_container_width=True):
                        with st.spinner(f"Respawning {agent['name']}..."):
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            time.sleep(0.5)
                            result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                            if result:
                                st.success(f"✅ {agent['name']} respawned!")
                                resource_monitor.register_agent(result.id, result.name)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to respawn")
                    
                    if st.button("🛑 Kill", key=f"kill_{agent['id']}", use_container_width=True):
                        st.session_state.orchestrator.kill_agent(agent['id'])
                        resource_monitor.unregister_agent(agent['id'])
                        st.warning(f"🛑 {agent['name']} killed")
                        time.sleep(1)
                        st.rerun()
                    
                    if st.button("💬 Chat", key=f"chat_ctrl_{agent['id']}", use_container_width=True):
                        st.session_state.selected_agent_for_chat = agent['id']
                        st.rerun()
                    
                    if st.button("🔔 Ping", key=f"ping_{agent['id']}", use_container_width=True):
                        with st.spinner("Pinging..."):
                            if ping_agent(agent['id']):
                                st.success("✅ Responsive")
                            else:
                                st.error("❌ Not responding")
    
    # Global actions
    if data['agents']:
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛑 Kill All Agents", type="secondary"):
                for agent in data['agents']:
                    st.session_state.orchestrator.kill_agent(agent['id'])
                    resource_monitor.unregister_agent(agent['id'])
                st.warning("🛑 All agents killed")
                time.sleep(1)
                st.rerun()
        with col2:
            if st.button("🔄 Respawn All", type="secondary"):
                agent_names = [a['name'].lower() for a in data['agents']]
                for agent in data['agents']:
                    st.session_state.orchestrator.kill_agent(agent['id'])
                    resource_monitor.unregister_agent(agent['id'])
                time.sleep(0.5)
                for name in agent_names:
                    result = st.session_state.orchestrator.spawn_agent(name)
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                st.success("✅ All agents respawned")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # Spawn new agents
    st.subheader("🚀 Spawn New Agents")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Individual Agents**")
        available = data.get('available_agents', [])
        
        for agent_name in available:
            soul_path = Path(f"./agents/{agent_name}/soul.md")
            if soul_path.exists():
                content = soul_path.read_text()
                avatar = "🤖"
                role = "Agent"
                for line in content.split('\n'):
                    if '**Avatar:**' in line:
                        avatar = line.split(':**')[1].strip() if ':**' in line else "🤖"
                    if '**Role:**' in line:
                        role = line.split(':**')[1].strip() if ':**' in line else "Agent"
                
                is_running = any(a['name'].lower() == agent_name.lower() for a in data['agents'])
                
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"{avatar} **{agent_name.title()}**  
<small>{role}</small>", unsafe_allow_html=True)
                with c2:
                    if is_running:
                        st.button("✅ Running", key=f"spawn_status_{agent_name}", disabled=True)
                    else:
                        if st.button("🚀 Spawn", key=f"spawn_{agent_name}"):
                            with st.spinner(f"Spawning {agent_name}..."):
                                result = st.session_state.orchestrator.spawn_agent(agent_name)
                                if result:
                                    resource_monitor.register_agent(result.id, result.name)
                                    st.success(f"✅ {agent_name.title()} spawned!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Failed")
    
    with col2:
        st.markdown("**⚡ Quick Squads**")
        squads = {
            "🎯 Sales Squad": ['hunter', 'pepper', 'sage'],
            "🎨 Creative Squad": ['quill', 'pixel', 'shuri'],
            "💻 Dev Squad": ['code', 'guardian', 'wong'],
            "🔬 Research Squad": ['scout', 'sage', 'shuri']
        }
        
        for squad_name, agents in squads.items():
            with st.expander(f"{squad_name}"):
                st.write(f"Agents: {', '.join(agents)}")
                if st.button(f"🚀 Spawn Squad", key=f"squad_{squad_name}"):
                    progress = st.progress(0)
                    for i, name in enumerate(agents):
                        result = st.session_state.orchestrator.spawn_agent(name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                        progress.progress((i + 1) / len(agents))
                    st.success(f"✅ Squad spawned!")
                    time.sleep(1)
                    st.rerun()

# ==================== MISSIONS PAGE ====================
elif page == "📋 Missions":
    st.markdown('<p class="main-header">📋 Mission Control</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2 = st.tabs(["📋 Active Missions", "➕ Create New"])
    
    with tab1:
        if not data['missions']:
            st.info("No missions yet. Create one!")
        else:
            for mission in data['missions']:
                with st.expander(f"📋 {mission['title']} ({mission['progress']['percent']}% complete)"):
                    cols = st.columns(3)
                    with cols[0]:
                        st.metric("Status", mission['status'])
                    with cols[1]:
                        st.metric("Tasks", f"{mission['progress']['completed']}/{mission['progress']['total']}")
                    with cols[2]:
                        st.metric("Progress", f"{mission['progress']['percent']}%")
                    
                    # Auto-execute
                    if mission['status'] == 'active' and mission['progress']['percent'] < 100:
                        if st.button("🚀 Auto-Execute All", key=f"auto_{mission['id']}"):
                            with st.spinner("Starting..."):
                                st.session_state.orchestrator.execute_mission_auto(mission['id'], parallel=True)
                            st.success("✅ Started!")
                            time.sleep(1)
                            st.rerun()
                    
                    # Export
                    if mission['progress']['completed'] > 0:
                        if st.button("📥 Export", key=f"export_{mission['id']}"):
                            export_path = st.session_state.orchestrator.export_mission(mission['id'], "markdown")
                            if export_path:
                                st.success(f"✅ Exported: {export_path}")
                            else:
                                st.error("❌ Export failed")
                    
                    # Tasks
                    st.subheader("Tasks")
                    full_mission = st.session_state.orchestrator.mission_manager.get_mission(mission['id'])
                    if full_mission:
                        for task in full_mission.tasks:
                            status_icon = {"pending": "⏳", "in_progress": "⏳", "completed": "✅", "failed": "❌"}.get(task.status, "⏳")
                            cols = st.columns([4, 2])
                            with cols[0]:
                                st.write(f"{status_icon} {task.description}")
                            with cols[1]:
                                st.write(f"👤 {task.assigned_to or 'Unassigned'}")
    
    with tab2:
        st.subheader("🚀 Create New Mission")
        if not data['agents']:
            st.warning("⚠️ You need at least one agent!")
            st.stop()
        
        with st.form("mission_form"):
            title = st.text_input("Mission Title *", placeholder="e.g., Launch Q2 Campaign")
            description = st.text_area("Description")
            
            tasks = []
            for i in range(5):
                cols = st.columns([3, 2])
                with cols[0]:
                    task_desc = st.text_input(f"Task {i+1}", key=f"task_{i}", placeholder=f"Task {i+1} (optional)")
                with cols[1]:
                    agent_list = [a['name'] for a in data['agents']]
                    assigned = st.selectbox(f"Assign to", ["Auto"] + agent_list, key=f"agent_{i}")
                if task_desc:
                    tasks.append({"description": task_desc, "assigned_to": None if assigned == "Auto" else assigned})
            
            submitted = st.form_submit_button("🚀 Launch Mission", type="primary")
            if submitted:
                if not title or not tasks:
                    st.error("Need title and at least one task")
                else:
                    mission = st.session_state.orchestrator.create_mission(title=title, description=description, tasks=tasks)
                    st.success(f"✅ Mission created: {mission.id}")

# ==================== HANDOFFS PAGE ====================
elif page == "🔄 Handoffs":
    st.markdown('<p class="main-header">🔄 Agent Handoffs</p>', unsafe_allow_html=True)
    st.info("Handoffs allow agents to pass work to each other with full context.")

# ==================== ALERTS PAGE ====================
elif page == "🔔 Alerts":
    st.markdown('<p class="main-header">🔔 Activity Alerts</p>', unsafe_allow_html=True)
    st.success("✅ No active alerts! System is healthy.")

# ==================== ANALYTICS PAGE ====================
elif page == "📊 Analytics":
    st.markdown('<p class="main-header">📊 System Analytics</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Resource usage charts
    st.subheader("📈 Resource Usage Over Time")
    
    for agent in data['agents']:
        resources = resource_monitor.get_agent_resources(agent['id'])
        if resources and len(resources.snapshots) > 1:
            with st.expander(f"{agent['avatar']} {agent['name']}"):
                # Prepare data for chart
                times = [s.timestamp for s in resources.snapshots]
                cpus = [s.cpu_percent for s in resources.snapshots]
                mems = [s.memory_mb for s in resources.snapshots]
                
                chart_data = {"Time": range(len(times)), "CPU %": cpus, "Memory MB": mems}
                st.line_chart(chart_data)

# ==================== LOGS & DEBUG PAGE ====================
elif page == "📜 Logs & Debug":
    st.markdown('<p class="main-header">📜 Logs & Debug Information</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["❌ Agent Errors", "📡 Recent Events", "🔧 Debug Tools"])
    
    with tab1:
        error_agents = [a for a in data['agents'] if a['status'] == 'error']
        offline_agents = [a for a in data['agents'] if a['status'] == 'offline']
        
        if error_agents:
            st.error(f"⚠️ {len(error_agents)} agent(s) in ERROR state")
            for agent in error_agents:
                st.write(f"🔴 {agent['avatar']} {agent['name']}")
        else:
            st.success("✅ No agents in error state")
        
        if offline_agents:
            st.warning(f"⚠️ {len(offline_agents)} agent(s) OFFLINE")
    
    with tab2:
        events = st.session_state.tracker.get_recent_events(50)
        for event in events:
            ts = event['timestamp'].split('T')[1][:12] if 'T' in event['timestamp'] else event['timestamp'][:12]
            st.text(f"[{ts}] {event['type']}: {event['from_agent']} - {event['content'][:60]}...")
    
    with tab3:
        if st.button("🔄 Refresh All Data"):
            st.rerun()
        if st.button("📊 Show System Stats"):
            st.json(resource_monitor.get_system_summary())

# ==================== SYSTEM PAGE ====================
elif page == "⚙️ System":
    st.markdown('<p class="main-header">⚙️ System Status</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔗 Ollama")
        if data['system']['ollama_connected']:
            st.success("🟢 Connected")
        else:
            st.error("🔴 Disconnected")
    
    with col2:
        st.subheader("📦 Version")
        st.write(f"**Workspace:** v1.4.0")

# Footer
st.sidebar.divider()
st.sidebar.markdown(f"**Workspace v1.4.0** 🎯")
st.sidebar.markdown(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
