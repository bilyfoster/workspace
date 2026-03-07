#!/usr/bin/env python3
"""
Workspace Dashboard

Mission Control-style web interface with:
- Real-time activity monitoring
- Agent-to-agent conversation tracking
- Handoff management
- Mission board

Usage:
    streamlit run dashboard.py
"""
import streamlit as st
import requests
import json
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from workspace_orchestrator import get_orchestrator, WorkspaceOrchestrator
from shared.bus.activity_tracker import tracker, ActivityTracker
from shared.bus.handoff import handoff_manager, HandoffManager, HandoffContext

# Page config
st.set_page_config(
    page_title="Workspace | Mission Control",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Mission Control look
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
    }
    .status-online { color: #00cc00; font-weight: bold; }
    .status-working { color: #ff9900; font-weight: bold; }
    .status-offline { color: #cc0000; font-weight: bold; }
    .status-idle { color: #00cc00; font-weight: bold; }
    .mission-board {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        min-height: 400px;
    }
    .task-card {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
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
    .activity-message {
        padding: 0.25rem 0;
        border-bottom: 1px solid #333;
    }
    .timestamp { color: #858585; font-size: 0.8em; }
    .agent-name { color: #4ec9b0; font-weight: bold; }
    .handoff-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .conversation-bubble {
        background-color: #e3f2fd;
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        max-width: 80%;
    }
    .conversation-bubble.sent {
        background-color: #e8f5e9;
        margin-left: auto;
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
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'selected_mission' not in st.session_state:
    st.session_state.selected_mission = None

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Sidebar
st.sidebar.markdown("# 🎯 Workspace")
st.sidebar.markdown("### Mission Control")

# Auto-refresh toggle
st.session_state.auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (sec)", 5, 60, 10)

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Activity Feed 🔥", "Agent Chat 💬", "Agents", "Missions", 
     "Handoffs 🔄", "Create Mission", "System"]
)

# Auto-refresh
if st.session_state.auto_refresh:
    time.sleep(0.1)

# ============== DASHBOARD PAGE ==============
if page == "Dashboard":
    st.markdown('<p class="main-header">🎯 Mission Control Dashboard</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # System status bar
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
        # Get recent handoffs
        recent_handoffs = st.session_state.handoff_manager.get_recent_handoffs(5)
        st.markdown(f"""
        <div class="metric-card">
            <h2>{len(recent_handoffs)}</h2>
            <p>Recent Handoffs</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Three-column layout: Squad | Mission Board | Live Activity
    col_squad, col_missions, col_activity = st.columns([1, 2, 1])
    
    with col_squad:
        st.subheader("👥 Active Squad")
        
        if not data['agents']:
            st.info("No agents running. Go to 'Agents' page to spawn.")
        
        for agent in data['agents']:
            status_class = f"status-{agent['status']}"
            current = agent['current_task'] or "Idle"
            if len(current) > 35:
                current = current[:35] + "..."
            
            st.markdown(f"""
            <div class="agent-card">
                <h4>{agent['avatar']} {agent['name']}</h4>
                <p><span class="{status_class}">●</span> {agent['status'].title()}</p>
                <p><small>{agent['role']}</small></p>
                <p><small>📝 {current}</small></p>
            </div>
            """, unsafe_allow_html=True)
    
    with col_missions:
        st.subheader("📋 Mission Board")
        
        if not data['missions']:
            st.info("No missions yet. Create one in 'Create Mission' tab.")
        else:
            todo_col, doing_col, done_col = st.columns(3)
            
            with todo_col:
                st.markdown("**📥 To Do**")
                for mission in data['missions']:
                    if mission['status'] == 'active' and mission['progress']['percent'] == 0:
                        st.markdown(f"""
                        <div class="task-card">
                            <strong>{mission['title']}</strong>
                            <br><small>{mission['tasks']} tasks</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            with doing_col:
                st.markdown("**🔵 In Progress**")
                for mission in data['missions']:
                    if mission['status'] == 'active' and 0 < mission['progress']['percent'] < 100:
                        progress = mission['progress']
                        st.markdown(f"""
                        <div class="task-card">
                            <strong>{mission['title']}</strong>
                            <br><small>{progress['completed']}/{progress['total']} tasks ({progress['percent']}%)</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            with done_col:
                st.markdown("**✅ Done**")
                for mission in data['missions']:
                    if mission['status'] == 'completed' or mission['progress']['percent'] == 100:
                        st.markdown(f"""
                        <div class="task-card" style="opacity: 0.7;">
                            <strong>{mission['title']}</strong>
                            <br><small>✓ Complete</small>
                        </div>
                        """, unsafe_allow_html=True)
    
    with col_activity:
        st.subheader("📡 Live Activity")
        
        events = st.session_state.tracker.get_recent_events(10)
        
        if not events:
            st.info("No activity yet...")
        else:
            for event in events:
                timestamp = event['timestamp'].split('T')[1][:8] if 'T' in event['timestamp'] else event['timestamp'][:8]
                
                # Format based on event type
                if event['type'] == 'agent_message':
                    icon = "💬"
                    text = f"{event['from_agent']} → {event['to_agent']}"
                elif event['type'] == 'task_completed':
                    icon = "✅"
                    text = f"{event['from_agent']} completed task"
                elif event['type'] == 'task_started':
                    icon = "🔵"
                    text = f"{event['from_agent']} started task"
                elif 'handoff' in event['type']:
                    icon = "🔄"
                    text = event['content'][:40]
                elif event['type'] == 'agent_online':
                    icon = "🟢"
                    text = f"{event['from_agent']} online"
                else:
                    icon = "•"
                    text = event['content'][:40]
                
                st.markdown(f"""
                <small><code>{timestamp}</code> {icon} {text}...</small>
                """, unsafe_allow_html=True)

# ============== ACTIVITY FEED PAGE ==============
elif page == "Activity Feed 🔥":
    st.markdown('<p class="main-header">📡 Activity Monitor</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Real-time Activity Feed")
        
        events = st.session_state.tracker.get_recent_events(100)
        
        if not events:
            st.info("No activity recorded yet. Spawn agents and start missions!")
        else:
            # Filter options
            event_types = list(set(e['type'] for e in events))
            selected_types = st.multiselect("Filter by type", event_types, default=event_types)
            
            filtered_events = [e for e in events if e['type'] in selected_types]
            
            # Display as activity feed
            st.markdown('<div class="activity-feed">', unsafe_allow_html=True)
            
            for event in reversed(filtered_events):  # Newest first
                timestamp = event['timestamp'].split('T')[1][:12] if 'T' in event['timestamp'] else event['timestamp'][:12]
                
                # Type-based styling
                type_colors = {
                    'agent_message': '#4ec9b0',
                    'task_completed': '#b5cea8',
                    'task_started': '#ce9178',
                    'handoff_request': '#c586c0',
                    'handoff_accept': '#b5cea8',
                    'agent_online': '#4ec9b0',
                    'agent_offline': '#f44747',
                }
                color = type_colors.get(event['type'], '#d4d4d4')
                
                # Format content
                if event['to_agent']:
                    direction = f"{event['from_agent']} → {event['to_agent']}"
                else:
                    direction = event['from_agent']
                
                st.markdown(f"""
                <div class="activity-message">
                    <span class="timestamp">[{timestamp}]</span>
                    <span style="color: {color}">[{event['type']}]</span>
                    <span class="agent-name">{direction}</span>: {event['content'][:80]}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.subheader("Activity Summary")
        
        summary = st.session_state.tracker.get_activity_summary()
        
        st.metric("Total Events", summary['total_events'])
        st.metric("Active Agents", summary['active_agents'])
        st.metric("Missions Tracked", summary['missions_tracked'])
        
        st.divider()
        
        st.subheader("Event Breakdown")
        for event_type, count in sorted(summary['event_types'].items(), key=lambda x: x[1], reverse=True):
            st.write(f"{event_type}: {count}")
        
        st.divider()
        
        st.subheader("Most Active Agents")
        for agent_id, count in summary['top_agents']:
            st.write(f"{agent_id}: {count} events")

# ============== AGENT CHAT PAGE ==============
elif page == "Agent Chat 💬":
    st.markdown('<p class="main-header">💬 Agent Conversations</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Select conversation
    agent_list = [a['name'] for a in data['agents']]
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Select Conversation")
        
        # Who's talking to whom
        conversations = st.session_state.tracker.get_activity_summary()['conversations']
        
        if not conversations:
            st.info("No conversations yet. Agents need to message each other via handoffs.")
        
        selected_conv = None
        for conv in conversations:
            agents = conv['agents']
            if st.button(f"{' ↔ '.join(agents)} ({conv['message_count']} msgs)", key=f"conv_{'_'.join(agents)}"):
                selected_conv = agents
        
        st.divider()
        
        st.subheader("Start New Conversation")
        from_agent = st.selectbox("From Agent", agent_list)
        to_agent = st.selectbox("To Agent", [a for a in agent_list if a != from_agent])
        message = st.text_area("Message")
        
        if st.button("Send Message", type="primary"):
            # Find agent IDs
            from_id = None
            to_id = None
            for agent in data['agents']:
                if agent['name'] == from_agent:
                    from_id = agent['id']
                if agent['name'] == to_agent:
                    to_id = agent['id']
            
            if from_id and to_id:
                from shared.bus.message_bus import Message, MessageType
                msg = Message.create(
                    MessageType.AGENT_MESSAGE,
                    sender=from_id,
                    recipient=to_id,
                    payload={'content': message}
                )
                st.session_state.orchestrator.bus.publish(msg)
                st.success("Message sent!")
                time.sleep(1)
                st.rerun()
    
    with col2:
        st.subheader("Conversation View")
        
        if selected_conv:
            # Get conversation history
            events = st.session_state.tracker.get_agent_conversation(
                selected_conv[0], selected_conv[1], limit=50
            )
            
            for event in events:
                is_sent = event['from_agent'] == selected_conv[0]
                bubble_class = "sent" if is_sent else ""
                
                st.markdown(f"""
                <div class="conversation-bubble {bubble_class}">
                    <small><strong>{event['from_agent']}</strong></small><br>
                    {event['content']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Select a conversation from the left to view messages")

# ============== HANDOFFS PAGE ==============
elif page == "Handoffs 🔄":
    st.markdown('<p class="main-header">🔄 Agent Handoffs</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2 = st.tabs(["Recent Handoffs", "Create Handoff"])
    
    with tab1:
        st.subheader("Recent Handoff Activity")
        
        handoffs = st.session_state.handoff_manager.get_recent_handoffs(20)
        
        if not handoffs:
            st.info("No handoffs yet. Create one to see agents collaborate!")
        
        for handoff in handoffs:
            status_icon = {
                'pending': '⏳',
                'accepted': '✅',
                'rejected': '❌',
                'completed': '✓',
                'failed': '💥'
            }.get(handoff['status'], '?')
            
            with st.expander(f"{status_icon} {handoff['from_agent']} → {handoff['to_agent']} ({handoff['status']})"):
                st.write(f"**Reason:** {handoff.get('reason', 'No reason given')}")
                st.write(f"**Original Task:** {handoff['context']['original_task'][:100]}...")
                st.write(f"**Work Done:** {handoff['context']['work_done'][:100]}...")
                
                if handoff['context']['next_steps']:
                    st.write("**Next Steps:**")
                    for step in handoff['context']['next_steps']:
                        st.write(f"  - {step}")
    
    with tab2:
        st.subheader("Create New Handoff")
        
        agent_list = [a['name'] for a in data['agents']]
        
        from_agent = st.selectbox("From Agent (handing off)", agent_list)
        to_agent = st.selectbox("To Agent (receiving)", [a for a in agent_list if a != from_agent])
        
        original_task = st.text_input("Original Task")
        work_done = st.text_area("Work Completed So Far")
        
        col1, col2 = st.columns(2)
        with col1:
            findings = st.text_area("Key Findings (one per line)").split('\n')
        with col2:
            next_steps = st.text_area("Suggested Next Steps (one per line)").split('\n')
        
        reason = st.text_input("Handoff Reason")
        
        if st.button("🔄 Initiate Handoff", type="primary"):
            # Find agent IDs
            from_id = next((a['id'] for a in data['agents'] if a['name'] == from_agent), None)
            to_id = next((a['id'] for a in data['agents'] if a['name'] == to_agent), None)
            
            if from_id and to_id:
                context = HandoffContext(
                    original_task=original_task,
                    work_done=work_done,
                    findings={f"finding_{i}": f for i, f in enumerate(findings) if f},
                    next_steps=[s for s in next_steps if s],
                    questions=[],
                    files=[],
                    notes=reason
                )
                
                handoff_id = st.session_state.handoff_manager.request_handoff(
                    from_agent=from_id,
                    to_agent=to_id,
                    context=context,
                    reason=reason
                )
                
                st.success(f"Handoff {handoff_id} initiated!")
                time.sleep(1)
                st.rerun()

# ============== AGENTS PAGE ==============
elif page == "Agents":
    st.markdown('<p class="main-header">🤖 Agent Management</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Spawn Agents")
        available = data['available_agents']
        
        if not available:
            st.warning("No agent souls found in ./agents/")
        else:
            selected = st.multiselect("Select agents to spawn", available, default=[])
            
            if st.button("🚀 Spawn Selected Agents", type="primary"):
                for agent_name in selected:
                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                    if result:
                        st.success(f"Spawned {agent_name}")
                    else:
                        st.error(f"Failed to spawn {agent_name}")
                time.sleep(1)
                st.rerun()
    
    with col2:
        st.subheader("⚡ Quick Squads")
        
        squads = {
            "🎯 Sales Squad": ['hunter', 'pepper', 'sage'],
            "🎨 Creative Squad": ['quill', 'pixel', 'pepper'],
            "💻 Dev Squad": ['code', 'guardian', 'wong'],
            "🔬 Research Squad": ['scout', 'sage', 'shuri'],
            "🌍 Global Squad": ['lingua', 'scout', 'quill']
        }
        
        for squad_name, members in squads.items():
            if st.button(f"Spawn {squad_name}"):
                for name in members:
                    st.session_state.orchestrator.spawn_agent(name)
                st.success(f"{squad_name} spawned!")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # Agent activity
    st.subheader("📊 Agent Activity")
    
    if data['agents']:
        for agent in data['agents']:
            with st.expander(f"{agent['avatar']} {agent['name']} - {agent['status']}"):
                activity = st.session_state.tracker.get_agent_activity(agent['id'], limit=10)
                
                if activity:
                    for event in activity:
                        st.write(f"• [{event['type']}] {event['content'][:60]}...")
                else:
                    st.write("No activity yet")
    else:
        st.info("No active agents")

# ============== MISSIONS PAGE ==============
elif page == "Missions":
    st.markdown('<p class="main-header">📋 Mission Control</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # Mission selector
    mission_options = {m['id']: m['title'] for m in data['missions']}
    if mission_options:
        selected = st.selectbox("Select Mission", options=list(mission_options.keys()), 
                               format_func=lambda x: mission_options[x])
        
        mission = st.session_state.orchestrator.mission_manager.get_mission(selected)
        if mission:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", mission.status.value)
            with col2:
                total = len(mission.tasks)
                completed = len([t for t in mission.tasks if t.status == "completed"])
                st.metric("Progress", f"{completed}/{total}")
            with col3:
                percent = int((completed/total)*100) if total > 0 else 0
                st.metric("Complete", f"{percent}%")
            
            # Show mission activity
            st.subheader("Mission Activity Log")
            mission_activity = st.session_state.tracker.get_mission_activity(mission.id)
            
            if mission_activity:
                for event in mission_activity[-20:]:  # Last 20 events
                    st.write(f"[{event['type']}] {event['from_agent']}: {event['content'][:80]}...")
            
            # Task execution
            st.subheader("Tasks")
            for task in mission.tasks:
                status_icon = {"pending": "⏳", "in_progress": "🔵", "completed": "✅", "failed": "❌"}.get(task.status, "⏳")
                
                with st.expander(f"{status_icon} {task.description[:60]}..."):
                    st.write(f"**Status:** {task.status}")
                    st.write(f"**Assigned to:** {task.assigned_to or 'Unassigned'}")
                    
                    if task.result:
                        st.write("**Result:**")
                        st.code(task.result[:500] + "..." if len(task.result) > 500 else task.result)
                    
                    if task.status == "pending":
                        agent_list = [a['name'] for a in data['agents'] if a['status'] == 'idle']
                        if agent_list:
                            assign_to = st.selectbox(f"Assign to", agent_list, key=f"assign_{task.id}")
                            if st.button("Assign & Execute", key=f"exec_{task.id}"):
                                st.session_state.orchestrator.assign_task(
                                    assign_to, task.description, mission.id
                                )
                                st.success(f"Assigned to {assign_to}")
                                time.sleep(1)
                                st.rerun()
    else:
        st.info("No missions created yet. Go to 'Create Mission' tab.")

# ============== CREATE MISSION PAGE ==============
elif page == "Create Mission":
    st.markdown('<p class="main-header">🚀 Create New Mission</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    with st.form("mission_form"):
        title = st.text_input("Mission Title", placeholder="e.g., Launch Q2 Marketing Campaign")
        description = st.text_area("Description", placeholder="What do you want to accomplish?")
        
        st.subheader("Tasks")
        
        tasks = []
        for i in range(5):
            col1, col2 = st.columns([3, 1])
            with col1:
                task_desc = st.text_input(f"Task {i+1}", key=f"task_{i}", placeholder=f"Task description (optional)")
            with col2:
                available_agents = [a['name'] for a in data['agents']] if data['agents'] else []
                assigned = st.selectbox(f"Agent", ["Auto"] + available_agents, key=f"agent_{i}")
            
            if task_desc:
                tasks.append({
                    "description": task_desc,
                    "assigned_to": None if assigned == "Auto" else assigned
                })
        
        submitted = st.form_submit_button("🚀 Launch Mission", type="primary")
        
        if submitted and title and tasks:
            mission = st.session_state.orchestrator.create_mission(
                title=title,
                description=description,
                tasks=tasks
            )
            st.success(f"Mission created: {mission.id}")

# ============== SYSTEM PAGE ==============
elif page == "System":
    st.markdown('<p class="main-header">⚙️ System Status</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔗 Ollama Connection")
        if data['system']['ollama_connected']:
            st.success("🟢 Connected")
        else:
            st.error("🔴 Disconnected")
        
        st.write(f"**Host:** {st.session_state.orchestrator.ollama.host}")
    
    with col2:
        st.subheader("📈 Message Bus")
        bus_status = st.session_state.orchestrator.bus.get_agent_status()
        st.write(f"**Registered Agents:** {bus_status['registered_agents']}")
        st.write(f"**Total Messages:** {bus_status['message_count']}")

# Footer
st.sidebar.divider()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Workspace v1.0** 🎯  
Running on Herbie  
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
