#!/usr/bin/env python3
"""
Workspace Dashboard v1.1.5

Mission Control-style web interface with real-time agent interaction.

Usage:
    streamlit run dashboard.py

Version: v1.1.5
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from workspace_orchestrator import get_orchestrator, WorkspaceOrchestrator
from shared.bus.activity_tracker import tracker, ActivityTracker
from shared.bus.handoff import handoff_manager, HandoffManager, HandoffContext
from shared.bus.group_chat import group_chat_manager, GroupChatManager, GroupChatType
from shared.bus.alerts import alert_manager, AlertManager, AlertSeverity
from shared.bus.analytics import analytics, AnalyticsCollector

# Page config
st.set_page_config(
    page_title="Workspace | Mission Control v1.1.5",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        transition: all 0.3s;
    }
    .agent-card:hover {
        transform: translateX(5px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .status-online { color: #00cc00; font-weight: bold; }
    .status-working { color: #ff9900; font-weight: bold; }
    .status-offline { color: #cc0000; font-weight: bold; }
    .status-idle { color: #00cc00; font-weight: bold; }
    .chat-container {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 20px;
        max-height: 500px;
        overflow-y: auto;
    }
    .chat-message-user {
        background-color: #667eea;
        color: white;
        border-radius: 15px 15px 0 15px;
        padding: 12px 16px;
        margin: 8px 0 8px auto;
        max-width: 80%;
        float: right;
        clear: both;
    }
    .chat-message-agent {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 15px 15px 15px 0;
        padding: 12px 16px;
        margin: 8px auto 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
    }
    .spawn-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .spawn-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .activity-feed {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border-radius: 10px;
        padding: 1rem;
        font-family: 'Courier New', monospace;
        max-height: 600px;
        overflow-y: auto;
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
if 'analytics' not in st.session_state:
    st.session_state.analytics = analytics
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Sidebar
st.sidebar.markdown("# 🎯 Workspace")
st.sidebar.markdown("### Mission Control v1.1.5")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "💬 Chat 1-on-1", "👥 Group Chat", "🤖 Spawn Agents", "📋 Missions", 
     "🔄 Handoffs", "🔔 Alerts", "📊 Analytics", "📜 Logs & Debug", "⚙️ System"]
)

# ============== DASHBOARD PAGE ==============
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">🎯 Mission Control Dashboard</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Quick Start: Spawn Hunter", use_container_width=True):
            with st.spinner("Spawning Hunter..."):
                result = st.session_state.orchestrator.spawn_agent("hunter")
                if result:
                    st.success(f"✅ Hunter spawned! ID: {result.id}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to spawn Hunter")
    
    with col2:
        st.markdown("<a href='#chat-with-agents'><button style='width:100%; padding:10px;'>💬 Start Chat</button></a>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<a href='#create-mission'><button style='width:100%; padding:10px;'>➕ Create Mission</button></a>", unsafe_allow_html=True)
    
    st.divider()
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{len(data['agents'])}</h2>
            <p>Active Agents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        working = len([a for a in data['agents'] if a['status'] == 'working'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{working}</h2>
            <p>Working Now</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        active_missions = len([m for m in data['missions'] if m['status'] == 'active'])
        st.markdown(f"""
        <div class="metric-card">
            <h2>{active_missions}</h2>
            <p>Active Missions</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        active_alerts = len(data.get('active_alerts', []))
        st.markdown(f"""
        <div class="metric-card">
            <h2>{active_alerts}</h2>
            <p>Alerts</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Live Squad
    st.subheader("👥 Your Squad")
    
    if not data['agents']:
        st.info("🤖 No agents active. Go to '🤖 Spawn Agents' to get started!")
    else:
        agent_cols = st.columns(min(len(data['agents']), 4))
        for idx, agent in enumerate(data['agents']):
            with agent_cols[idx % 4]:
                status_color = "🟢" if agent['status'] == 'idle' else "🔵" if agent['status'] == 'working' else "🔴"
                st.markdown(f"""
                <div class="agent-card">
                    <h3>{agent['avatar']} {agent['name']}</h3>
                    <p>{status_color} <b>{agent['status'].upper()}</b></p>
                    <p><small>{agent['role']}</small></p>
                    <p><small>✅ {agent['tasks_completed']} tasks</small></p>
                </div>
                """, unsafe_allow_html=True)

# ============== CHAT 1-ON-1 PAGE ==============
elif page == "💬 Chat 1-on-1":
    st.markdown('<p class="main-header">💬 Chat with Your Agents</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    if not data['agents']:
        st.warning("🤖 No agents available. Spawn an agent first!")
        st.info("👈 Go to '🤖 Spawn Agents' in the sidebar to create your first agent.")
        st.stop()
    
    # Select agent to chat with
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Select Agent")
        
        agent_options = {a['id']: f"{a['avatar']} {a['name']} ({a['status']})" for a in data['agents']}
        selected_agent_id = st.selectbox(
            "Choose an agent to chat with",
            options=list(agent_options.keys()),
            format_func=lambda x: agent_options[x]
        )
        
        # Get selected agent details
        selected_agent = next((a for a in data['agents'] if a['id'] == selected_agent_id), None)
        
        if selected_agent:
            st.markdown(f"""
            **{selected_agent['avatar']} {selected_agent['name']}**
            - Status: {selected_agent['status']}
            - Role: {selected_agent['role']}
            - Tasks: {selected_agent['tasks_completed']}
            - Model: {selected_agent['model'] or 'Default'}
            """)
            
            if selected_agent['current_task']:
                st.info(f"📝 Currently: {selected_agent['current_task'][:50]}...")
        
        st.divider()
        
        st.subheader("💡 Quick Prompts")
        quick_prompts = [
            "Introduce yourself",
            "What can you help me with?",
            "Tell me about your skills",
            "Help me plan a mission"
        ]
        
        for prompt in quick_prompts:
            if st.button(prompt, key=f"quick_{prompt}"):
                if selected_agent_id not in st.session_state.chat_history:
                    st.session_state.chat_history[selected_agent_id] = []
                
                # Add user message
                st.session_state.chat_history[selected_agent_id].append({
                    "role": "user", 
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send and get response
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
                    st.error("❌ No response from agent")
    
    with col2:
        st.subheader("💬 Conversation")
        
        # Load persistent chat history
        if selected_agent_id:
            persistent_history = st.session_state.orchestrator.chat_history.load_history(selected_agent_id)
            if persistent_history:
                # Convert to session format
                st.session_state.chat_history[selected_agent_id] = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in persistent_history
                ]
        
        # Initialize chat history for this agent if not loaded
        if selected_agent_id not in st.session_state.chat_history:
            st.session_state.chat_history[selected_agent_id] = []
        
        # Display chat
        chat_container = st.container()
        with chat_container:
            # Add export button
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
                        <div style="background-color: #667eea; color: white; border-radius: 15px 15px 0 15px; 
                                    padding: 10px 15px; margin: 5px 0 5px auto; max-width: 80%; text-align: right;">
                            <b>You:</b><br>{msg['content']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: white; border: 1px solid #ddd; border-radius: 15px 15px 15px 0; 
                                    padding: 10px 15px; margin: 5px auto 5px 0; max-width: 80%;">
                            <b>{selected_agent['name']}:</b><br>{msg['content']}
                        </div>
                        """, unsafe_allow_html=True)
        
        # Chat input
        st.divider()
        with st.form("chat_form", clear_on_submit=True):
            message = st.text_input("Type your message", key="chat_input")
            submitted = st.form_submit_button("Send 📤", use_container_width=True)
            
            if submitted and message:
                # Add user message to history
                st.session_state.chat_history[selected_agent_id].append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Show thinking spinner
                with st.spinner(f"{selected_agent['name']} is thinking..."):
                    # Send to agent and wait for response (sync)
                    response = st.session_state.orchestrator.chat_with_agent_sync(
                        selected_agent['name'],
                        message,
                        timeout=30
                    )
                
                if response:
                    # Add agent response to history
                    st.session_state.chat_history[selected_agent_id].append({
                        "role": "agent",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    st.rerun()
                else:
                    st.error("❌ No response from agent (timeout or error)")
        
        # Show recent activity for this agent
        st.divider()
        st.subheader("📡 Recent Activity")
        agent_activity = st.session_state.tracker.get_agent_activity(selected_agent_id, limit=5)
        if agent_activity:
            for event in agent_activity:
                timestamp = event['timestamp'].split('T')[1][:8] if 'T' in event['timestamp'] else ''
                st.text(f"[{timestamp}] {event['type']}: {event['content'][:60]}...")
        else:
            st.text("No recent activity")

# ============== GROUP CHAT PAGE ==============
elif page == "👥 Group Chat":
    st.markdown('<p class="main-header">👥 Group Chat with Your Squad</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    if len(data['agents']) < 2:
        st.warning("👥 You need at least 2 agents for a group chat!")
        st.info(f"You currently have {len(data['agents'])} agent(s). Spawn more agents first.")
        if st.button("➡️ Go to Spawn Agents"):
            st.experimental_set_query_params(page="Spawn Agents")
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
                    st.write(f"**Topic:** {group.get('topic', 'General discussion')}")
                    st.write(f"**Members:** {', '.join(group['members'])}")
                    st.write(f"**Messages:** {group['message_count']}")
                    
                    # Show recent messages
                    history = st.session_state.group_chat.get_group_history(group['id'], limit=10)
                    if history:
                        st.markdown("**Recent Messages:**")
                        for msg in history[-5:]:  # Show last 5
                            sender = msg['sender']
                            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                            st.markdown(f"<small><b>{sender}:</b> {content}</small>", unsafe_allow_html=True)
                    
                    # Send message to group
                    st.divider()
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
            
            group_type = st.selectbox(
                "Group Type",
                ["discussion", "workflow", "standup", "brainstorm", "review"],
                format_func=lambda x: {
                    "discussion": "💬 Discussion - General chat",
                    "workflow": "🔄 Workflow - Task coordination", 
                    "standup": "📅 Standup - Daily updates",
                    "brainstorm": "💡 Brainstorm - Idea generation",
                    "review": "👀 Review - Code/design reviews"
                }.get(x, x)
            )
            
            topic = st.text_input("Topic (optional)", placeholder="What is this group for?")
            
            st.write("**Select Members:**")
            agent_list = [(a['id'], f"{a['avatar']} {a['name']}") for a in data['agents']]
            
            selected_members = []
            for agent_id, agent_label in agent_list:
                if st.checkbox(agent_label, key=f"member_{agent_id}"):
                    # Get the actual agent name from the agent_list
                    agent_name = next((a['name'] for a in data['agents'] if a['id'] == agent_id), agent_id)
                    selected_members.append(agent_name)
            
            submitted = st.form_submit_button("👥 Create Group", type="primary", use_container_width=True)
            
            if submitted:
                if not group_name:
                    st.error("❌ Please enter a group name")
                elif len(selected_members) < 2:
                    st.error("❌ Select at least 2 agents for a group chat")
                else:
                    from shared.bus.group_chat import GroupChatType
                    group = st.session_state.group_chat.create_group(
                        name=group_name,
                        members=selected_members,
                        created_by="user",
                        chat_type=GroupChatType(group_type),
                        topic=topic
                    )
                    st.success(f"✅ Created group: {group.name} with {len(selected_members)} members!")
                    st.info("Go to '💬 Active Groups' to start chatting")
                    time.sleep(1)
                    st.rerun()

# ============== SPAWN AGENTS PAGE ==============
elif page == "🤖 Spawn Agents":
    st.markdown('<p class="main-header">🤖 Spawn Your AI Squad</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Current squad status
    st.subheader("👥 Current Squad")
    
    if data['agents']:
        # Management controls
        st.write("**Agent Management:**")
        
        for agent in data['agents']:
            status_emoji = "🟢" if agent['status'] == 'idle' else "🔵" if agent['status'] == 'working' else "🔴" if agent['status'] == 'error' else "⚪"
            thread_status = "✅" if agent.get('thread_alive') else "❌"
            
            with st.expander(f"{agent['avatar']} {agent['name']} {status_emoji} (Thread: {thread_status})"):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**Role:** {agent['role']}")
                    st.write(f"**Status:** {agent['status']}")
                    st.write(f"**Tasks:** {agent['tasks_completed']}")
                
                with col2:
                    if st.button("🔄 Respawn", key=f"respawn_{agent['id']}"):
                        with st.spinner(f"Respawning {agent['name']}..."):
                            # Kill old
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            time.sleep(1)
                            # Spawn new
                            result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                            if result:
                                st.success(f"✅ {agent['name']} respawned!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to respawn")
                
                with col3:
                    if st.button("🛑 Kill", key=f"kill_{agent['id']}"):
                        st.session_state.orchestrator.kill_agent(agent['id'])
                        st.warning(f"🛑 {agent['name']} killed")
                        time.sleep(1)
                        st.rerun()
                
                with col4:
                    if st.button("💬 Chat", key=f"chat_{agent['id']}"):
                        st.info(f"👈 Go to '💬 Chat 1-on-1' to talk to {agent['name']}")
        
        # Kill All button
        st.divider()
        if st.button("🛑 Kill All Agents", type="secondary"):
            for agent in data['agents']:
                st.session_state.orchestrator.kill_agent(agent['id'])
            st.warning("🛑 All agents killed")
            time.sleep(1)
            st.rerun()
            
    else:
        st.info("No agents running yet. Spawn some below!")
    
    st.divider()
    
    # Spawn section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Individual Agents")
        
        available = data['available_agents']
        
        if not available:
            st.error("No agent souls found in ./agents/")
        else:
            # Show agent cards
            for agent_name in available:
                soul_path = Path(f"./agents/{agent_name}/soul.md")
                if soul_path.exists():
                    content = soul_path.read_text()
                    # Extract avatar and role
                    avatar = "🤖"
                    role = "Agent"
                    for line in content.split('\n'):
                        if '**Avatar:**' in line:
                            avatar = line.split(':**')[1].strip() if ':**' in line else "🤖"
                        if '**Role:**' in line:
                            role = line.split(':**')[1].strip() if ':**' in line else "Agent"
                    
                    # Check if already running
                    is_running = any(a['name'].lower() == agent_name.lower() for a in data['agents'])
                    
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{avatar} {agent_name.title()}** - {role}")
                    with col_b:
                        if is_running:
                            st.button("✅ Running", key=f"status_{agent_name}", disabled=True)
                        else:
                            if st.button("🚀 Spawn", key=f"spawn_{agent_name}"):
                                with st.spinner(f"Spawning {agent_name}..."):
                                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                                    if result:
                                        st.success(f"✅ {agent_name.title()} spawned!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to spawn {agent_name}")
    
    with col2:
        st.subheader("⚡ Quick Squads")
        
        squads = {
            "🎯 Sales Squad": {
                "agents": ['hunter', 'pepper', 'sage'],
                "description": "Outreach, email marketing, and analytics"
            },
            "🎨 Creative Squad": {
                "agents": ['quill', 'pixel', 'pepper'],
                "description": "Social media, design, and campaigns"
            },
            "💻 Dev Squad": {
                "agents": ['code', 'guardian', 'wong'],
                "description": "Development, testing, and documentation"
            },
            "🔬 Research Squad": {
                "agents": ['scout', 'sage', 'shuri'],
                "description": "Research, analysis, and strategy"
            }
        }
        
        for squad_name, squad_info in squads.items():
            with st.expander(f"{squad_name}"):
                st.write(f"*{squad_info['description']}*")
                st.write(f"Agents: {', '.join(squad_info['agents'])}")
                
                if st.button(f"🚀 Spawn {squad_name}", key=f"squad_{squad_name}"):
                    spawned = []
                    failed = []
                    
                    progress = st.progress(0)
                    for i, name in enumerate(squad_info['agents']):
                        result = st.session_state.orchestrator.spawn_agent(name)
                        if result:
                            spawned.append(name)
                        else:
                            failed.append(name)
                        progress.progress((i + 1) / len(squad_info['agents']))
                    
                    if spawned:
                        st.success(f"✅ Spawned: {', '.join(spawned)}")
                    if failed:
                        st.error(f"❌ Failed: {', '.join(failed)}")
                    
                    time.sleep(1)
                    st.rerun()

# ============== MISSIONS PAGE ==============
elif page == "📋 Missions":
    st.markdown('<p class="main-header">📋 Mission Control</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2 = st.tabs(["📋 Active Missions", "➕ Create New"])
    
    with tab1:
        if not data['missions']:
            st.info("No missions yet. Create one in the '➕ Create New' tab!")
        else:
            for mission in data['missions']:
                with st.expander(f"📋 {mission['title']} ({mission['progress']['percent']}% complete)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Status", mission['status'])
                    with col2:
                        st.metric("Tasks", f"{mission['progress']['completed']}/{mission['progress']['total']}")
                    with col3:
                        st.metric("Progress", f"{mission['progress']['percent']}%")
                    
                    # Auto-execute button
                    if mission['status'] == 'active' and mission['progress']['percent'] < 100:
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if st.button("🚀 Auto-Execute All", key=f"auto_{mission['id']}"):
                                with st.spinner("Starting auto-execution..."):
                                    st.session_state.orchestrator.execute_mission_auto(mission['id'], parallel=True)
                                st.success("✅ Execution started! Tasks will run in parallel.")
                                time.sleep(1)
                                st.rerun()
                        
                        with col_b:
                            running = st.session_state.orchestrator.get_running_executions()
                            if mission['id'] in running:
                                st.info("⏳ Running...")
                        
                        with col_c:
                            pass  # Spacer
                    
                    # Export button
                    if mission['progress']['completed'] > 0:
                        if st.button("📥 Export Results", key=f"export_{mission['id']}"):
                            with st.spinner("Exporting..."):
                                export_path = st.session_state.orchestrator.export_mission(mission['id'], "markdown")
                                if export_path:
                                    st.success(f"✅ Exported to: {export_path}")
                                    # Show file content preview
                                    try:
                                        content = export_path.read_text()
                                        with st.expander("📄 Preview Export"):
                                            st.markdown(content[:2000] + "..." if len(content) > 2000 else content)
                                    except:
                                        pass
                                else:
                                    st.error("❌ Export failed")
                    
                    # Tasks
                    st.subheader("Tasks")
                    full_mission = st.session_state.orchestrator.mission_manager.get_mission(mission['id'])
                    if full_mission:
                        for task in full_mission.tasks:
                            status_icon = {"pending": "⏳", "in_progress": "🔵", "completed": "✅", "failed": "❌"}.get(task.status, "⏳")
                            
                            cols = st.columns([4, 2, 2])
                            with cols[0]:
                                st.write(f"{status_icon} {task.description}")
                            with cols[1]:
                                st.write(f"👤 {task.assigned_to or 'Unassigned'}")
                            with cols[2]:
                                if task.status == "pending":
                                    agent_list = [a['name'] for a in data['agents'] if a['status'] == 'idle']
                                    if agent_list and st.button("Assign & Run", key=f"run_{task.id}"):
                                        st.session_state.orchestrator.assign_task(
                                            agent_list[0], task.description, mission['id'], task.id
                                        )
                                        st.success(f"Assigned to {agent_list[0]}")
                                        time.sleep(1)
                                        st.rerun()
    
    with tab2:
        st.subheader("🚀 Create New Mission")
        
        if not data['agents']:
            st.warning("⚠️ You need at least one agent to create a mission!")
            if st.button("➡️ Spawn an Agent First"):
                st.switch_page("🤖 Spawn Agents")
            st.stop()
        
        with st.form("mission_form"):
            title = st.text_input("Mission Title *", placeholder="e.g., Launch Q2 Marketing Campaign")
            description = st.text_area("Description", placeholder="What do you want to accomplish?")
            
            st.subheader("Tasks")
            tasks = []
            for i in range(5):
                cols = st.columns([3, 2])
                with cols[0]:
                    task_desc = st.text_input(f"Task {i+1} description", key=f"task_{i}", placeholder=f"Task {i+1} (optional)")
                with cols[1]:
                    agent_list = [a['name'] for a in data['agents']]
                    assigned = st.selectbox(f"Assign to", ["Auto"] + agent_list, key=f"agent_{i}")
                
                if task_desc:
                    tasks.append({
                        "description": task_desc,
                        "assigned_to": None if assigned == "Auto" else assigned
                    })
            
            create_group = st.checkbox("Create group chat for this mission")
            
            submitted = st.form_submit_button("🚀 Launch Mission", type="primary", use_container_width=True)
            
            if submitted:
                if not title:
                    st.error("❌ Please enter a mission title")
                elif not tasks:
                    st.error("❌ Please add at least one task")
                else:
                    try:
                        mission = st.session_state.orchestrator.create_mission(
                            title=title, description=description, tasks=tasks
                        )
                        
                        if create_group:
                            agent_names = [t['assigned_to'] for t in tasks if t['assigned_to']]
                            if agent_names:
                                st.session_state.group_chat.create_workflow_group(
                                    mission_id=mission.id,
                                    mission_title=title,
                                    agents=agent_names
                                )
                        
                        st.success(f"✅ Mission created: {mission.id}")
                        st.info("📋 Go to 'Active Missions' tab to view and execute tasks")
                    except Exception as e:
                        st.error(f"❌ Error creating mission: {str(e)}")

# ============== HANDOFFS PAGE ==============
elif page == "🔄 Handoffs":
    st.markdown('<p class="main-header">🔄 Agent Handoffs</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    st.info("Handoffs allow agents to pass work to each other with full context.")
    
    handoffs = data.get('recent_handoffs', [])
    if handoffs:
        for handoff in handoffs:
            status_icon = {'pending': '⏳', 'accepted': '✅', 'rejected': '❌'}.get(handoff.get('status'), '?')
            st.markdown(f"{status_icon} {handoff.get('from_agent', '?')} → {handoff.get('to_agent', '?')}")
    else:
        st.text("No recent handoffs")

# ============== ALERTS PAGE ==============
elif page == "🔔 Alerts":
    st.markdown('<p class="main-header">🔔 Activity Alerts</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    alerts = data.get('active_alerts', [])
    if alerts:
        for alert in alerts:
            severity_colors = {'critical': '#ffcccc', 'error': '#ffe6cc', 'warning': '#ffffcc', 'info': '#e6f3ff'}
            color = severity_colors.get(alert['severity'], '#f0f0f0')
            st.markdown(f"""
            <div style="background-color: {color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <h4>{alert['title']} ({alert['severity'].upper()})</h4>
                <p>{alert['message']}</p>
                <small>Source: {alert['source']}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No active alerts! System is healthy.")

# ============== ANALYTICS PAGE ==============
elif page == "📊 Analytics":
    st.markdown('<p class="main-header">📊 System Analytics</p>', unsafe_allow_html=True)
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    metrics = data.get('system_metrics', {})
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Tasks", metrics.get('total_tasks', 0))
    with cols[1]:
        st.metric("Success Rate", f"{metrics.get('success_rate', 0)}%")
    with cols[2]:
        st.metric("Messages", metrics.get('total_messages', 0))
    with cols[3]:
        st.metric("Handoffs", metrics.get('total_handoffs', 0))
    
    st.divider()
    
    st.subheader("Agent Performance")
    perf_data = data.get('agent_performance', [])
    if perf_data:
        st.dataframe(perf_data, use_container_width=True)

# ============== LOGS & DEBUG PAGE ==============
elif page == "📜 Logs & Debug":
    st.markdown('<p class="main-header">📜 Logs & Debug Information</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2, tab3, tab4 = st.tabs(["❌ Agent Errors", "📡 Recent Events", "📋 Agent Details", "🔧 Debug Tools"])
    
    with tab1:
        st.subheader("Agent Errors & Issues")
        
        # Check for agents with error status
        error_agents = [a for a in data['agents'] if a['status'] == 'error']
        offline_agents = [a for a in data['agents'] if a['status'] == 'offline']
        
        if error_agents:
            st.error(f"⚠️ {len(error_agents)} agent(s) in ERROR state:")
            for agent in error_agents:
                with st.expander(f"🔴 {agent['avatar']} {agent['name']} - ERROR"):
                    st.write(f"**ID:** {agent['id']}")
                    st.write(f"**Role:** {agent['role']}")
                    st.write(f"**Last Task:** {agent.get('current_task', 'None')}")
                    st.write(f"**Thread Alive:** {agent.get('thread_alive', False)}")
                    
                    # Get recent activity for this agent
                    activity = st.session_state.tracker.get_agent_activity(agent['id'], limit=10)
                    if activity:
                        st.write("**Recent Activity:**")
                        for event in activity:
                            if event['type'] in ['task_failed', 'error']:
                                st.error(f"[{event['timestamp']}] {event['content'][:200]}")
        else:
            st.success("✅ No agents in error state")
        
        if offline_agents:
            st.warning(f"⚠️ {len(offline_agents)} agent(s) OFFLINE:")
            for agent in offline_agents:
                st.write(f"  - {agent['avatar']} {agent['name']}")
        
        st.divider()
        
        # Show failed tasks
        st.subheader("Failed Tasks")
        failed_events = [e for e in st.session_state.tracker.get_recent_events(100) 
                        if e['type'] == 'task_failed']
        
        if failed_events:
            for event in failed_events[:10]:
                st.error(f"**{event['from_agent']}**: {event['content'][:200]}")
        else:
            st.success("✅ No failed tasks recently")
    
    with tab2:
        st.subheader("Recent Activity Log")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            event_filter = st.multiselect(
                "Filter by event type",
                ['all', 'agent_online', 'agent_offline', 'task_started', 'task_completed', 
                 'task_failed', 'agent_message', 'error'],
                default=['all']
            )
        with col2:
            limit = st.slider("Number of events", 10, 200, 50)
        
        events = st.session_state.tracker.get_recent_events(limit)
        
        if 'all' not in event_filter:
            events = [e for e in events if e['type'] in event_filter]
        
        # Display with color coding
        for event in events:
            timestamp = event['timestamp'].split('T')[1][:12] if 'T' in event['timestamp'] else event['timestamp'][:12]
            
            # Color code by type
            if event['type'] == 'task_failed' or event['type'] == 'error':
                color = "#ffcccc"
                icon = "❌"
            elif event['type'] == 'agent_online':
                color = "#ccffcc"
                icon = "🟢"
            elif event['type'] == 'task_completed':
                color = "#ccffff"
                icon = "✅"
            else:
                color = "#f0f0f0"
                icon = "•"
            
            st.markdown(f"""
            <div style="background-color: {color}; padding: 8px; margin: 4px 0; border-radius: 4px; font-size: 0.9em;">
                <code>[{timestamp}]</code> {icon} <b>{event['type']}</b> | 
                {event['from_agent']} → {event.get('to_agent', 'broadcast')}: 
                {event['content'][:100]}...
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("Detailed Agent Information")
        
        for agent in data['agents']:
            with st.expander(f"{agent['avatar']} {agent['name']} ({agent['status']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**ID:** `{agent['id']}`")
                    st.write(f"**Role:** {agent['role']}")
                    st.write(f"**Status:** {agent['status']}")
                    st.write(f"**Model:** {agent.get('model', 'Default')}")
                with col2:
                    st.write(f"**Tasks Completed:** {agent['tasks_completed']}")
                    st.write(f"**Thread Alive:** {'✅ Yes' if agent.get('thread_alive') else '❌ No'}")
                    st.write(f"**Started:** {agent['started_at']}")
                
                if agent.get('current_task'):
                    st.info(f"📝 Current Task: {agent['current_task']}")
                
                # Check agent's message queue
                if agent['id'] in st.session_state.orchestrator.bus._agent_queues:
                    queue = st.session_state.orchestrator.bus._agent_queues[agent['id']]
                    if isinstance(queue, list):
                        st.write(f"**Pending Messages:** {len(queue)}")
                        for msg in queue:
                            st.text(f"  - {msg.type}")
    
    with tab4:
        st.subheader("🔧 Debug Tools")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Message Bus Status**")
            bus = st.session_state.orchestrator.bus
            st.write(f"Registered agents: {len(bus._agent_queues)}")
            st.write(f"Total messages: {len(bus._message_history)}")
            
            if st.button("🔄 Refresh All Data"):
                st.rerun()
        
        with col2:
            st.write("**Test Functions**")
            
            if st.button("🧪 Test MessageBus"):
                from shared.bus.message_bus import Message, MessageType
                test_msg = Message.create(
                    MessageType.SYSTEM_MESSAGE,
                    sender="user",
                    payload={"content": "Test message"}
                )
                st.success(f"✅ MessageBus working! Created message: {test_msg.id}")
            
            if st.button("📊 Show System Stats"):
                st.json({
                    "agents": len(data['agents']),
                    "messages": len(st.session_state.tracker.events),
                    "missions": len(data['missions']),
                    "ollama_connected": data['system']['ollama_connected']
                })

# ============== SYSTEM PAGE ==============
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
            st.error("🔴 Disconnected - Start Ollama with: ollama serve")
    
    with col2:
        st.subheader("📦 Version")
        st.write(f"**Workspace:** v1.1.5")
        st.write(f"**Commit:** 57473df")
        st.write("[GitHub](https://github.com/bilyfoster/workspace)")

# Footer
st.sidebar.divider()
st.sidebar.markdown(f"**Workspace v1.1.5** 🎯")
st.sidebar.markdown(f"Running on Herbie")
st.sidebar.markdown(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
