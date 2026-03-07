#!/usr/bin/env python3
"""
Workspace Dashboard v1.1.0

Mission Control-style web interface with:
- Real-time activity monitoring
- Agent-to-agent conversation tracking
- Handoff management
- Group chat support
- Activity alerts
- Time-based analytics

Usage:
    streamlit run dashboard.py

Version: v1.1.0
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
    page_title="Workspace | Mission Control v1.1.0",
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
    .version-footer {
        position: fixed;
        bottom: 0;
        right: 0;
        padding: 10px;
        background: #f0f2f6;
        font-size: 0.8em;
        color: #666;
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
    .alert-critical { background-color: #ffcccc; border-left: 4px solid #cc0000; padding: 10px; margin: 5px 0; }
    .alert-error { background-color: #ffe6cc; border-left: 4px solid #ff6600; padding: 10px; margin: 5px 0; }
    .alert-warning { background-color: #ffffcc; border-left: 4px solid #ffcc00; padding: 10px; margin: 5px 0; }
    .alert-info { background-color: #e6f3ff; border-left: 4px solid #0066cc; padding: 10px; margin: 5px 0; }
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
    .chat-message {
        background-color: #e3f2fd;
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        max-width: 80%;
    }
    .chat-message.own {
        background-color: #e8f5e9;
        margin-left: auto;
    }
    .group-card {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 2px solid #ddd;
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
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True
if 'selected_mission' not in st.session_state:
    st.session_state.selected_mission = None
if 'selected_group' not in st.session_state:
    st.session_state.selected_group = None

def get_dashboard_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Sidebar
st.sidebar.markdown("# 🎯 Workspace")
st.sidebar.markdown("### Mission Control v1.1.0")

# Auto-refresh toggle
st.session_state.auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (sec)", 5, 60, 10)

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "📡 Activity Feed", "💬 Group Chats", "🔄 Handoffs", "🔔 Alerts", "📊 Analytics", 
     "🤖 Agents", "📋 Missions", "➕ Create Mission", "⚙️ System"]
)

# Auto-refresh
if st.session_state.auto_refresh:
    time.sleep(0.1)

# ============== DASHBOARD PAGE ==============
if page == "🏠 Dashboard":
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
        active_alerts = len(data.get('active_alerts', []))
        st.markdown(f"""
        <div class="metric-card">
            <h2>{active_alerts}</h2>
            <p>Active Alerts</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        groups = len(data.get('groups', []))
        st.markdown(f"""
        <div class="metric-card">
            <h2>{groups}</h2>
            <p>Group Chats</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Three-column layout
    col_squad, col_missions, col_activity = st.columns([1, 2, 1])
    
    with col_squad:
        st.subheader("👥 Active Squad")
        
        if not data['agents']:
            st.info("No agents running. Go to '🤖 Agents' to spawn.")
        
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
            st.info("No missions. Create one in '➕ Create Mission' tab.")
        else:
            todo_col, doing_col, done_col = st.columns(3)
            
            with todo_col:
                st.markdown("**📥 To Do**")
                for mission in data['missions']:
                    if mission['status'] == 'active' and mission['progress']['percent'] == 0:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #ddd; border-radius:5px; padding:10px; margin:5px 0;">
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
                        <div style="background:white; border:1px solid #ddd; border-radius:5px; padding:10px; margin:5px 0;">
                            <strong>{mission['title']}</strong>
                            <br><small>{progress['completed']}/{progress['total']} ({progress['percent']}%)</small>
                        </div>
                        """, unsafe_allow_html=True)
            
            with done_col:
                st.markdown("**✅ Done**")
                for mission in data['missions']:
                    if mission['status'] == 'completed' or mission['progress']['percent'] == 100:
                        st.markdown(f"""
                        <div style="background:white; border:1px solid #ddd; border-radius:5px; padding:10px; margin:5px 0; opacity:0.7;">
                            <strong>{mission['title']}</strong>
                            <br><small>✓ Complete</small>
                        </div>
                        """, unsafe_allow_html=True)
    
    with col_activity:
        st.subheader("📡 Live Activity")
        
        # Show active alerts first
        alerts = data.get('active_alerts', [])
        if alerts:
            st.markdown("**🔔 Alerts**")
            for alert in alerts[:3]:
                severity_class = f"alert-{alert['severity']}"
                st.markdown(f"""
                <div class="{severity_class}">
                    <strong>{alert['title']}</strong><br>
                    <small>{alert['message'][:60]}...</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("**Recent Events**")
        events = st.session_state.tracker.get_recent_events(8)
        
        for event in events:
            timestamp = event['timestamp'].split('T')[1][:8] if 'T' in event['timestamp'] else event['timestamp'][:8]
            icon = {"agent_message": "💬", "task_completed": "✅", "task_started": "🔵", 
                   "handoff_request": "🔄", "agent_online": "🟢"}.get(event['type'], "•")
            
            st.markdown(f"<small><code>{timestamp}</code> {icon} {event['type'][:20]}</small>", unsafe_allow_html=True)

# ============== ACTIVITY FEED PAGE ==============
elif page == "📡 Activity Feed":
    st.markdown('<p class="main-header">📡 Activity Monitor</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Real-time Activity Feed")
        
        events = st.session_state.tracker.get_recent_events(200)
        
        if not events:
            st.info("No activity recorded. Spawn agents and start missions!")
        else:
            # Filters
            event_types = list(set(e['type'] for e in events))
            selected_types = st.multiselect("Filter by type", event_types, default=event_types)
            
            filtered_events = [e for e in events if e['type'] in selected_types]
            
            # Display
            st.markdown('<div class="activity-feed">', unsafe_allow_html=True)
            
            for event in reversed(filtered_events):
                timestamp = event['timestamp'].split('T')[1][:12] if 'T' in event['timestamp'] else event['timestamp'][:12]
                
                type_colors = {
                    'agent_message': '#4ec9b0', 'task_completed': '#b5cea8', 'task_started': '#ce9178',
                    'handoff_request': '#c586c0', 'handoff_accept': '#b5cea8', 'agent_online': '#4ec9b0',
                    'agent_offline': '#f44747'
                }
                color = type_colors.get(event['type'], '#d4d4d4')
                
                direction = f"{event['from_agent']} → {event['to_agent']}" if event['to_agent'] else event['from_agent']
                
                st.markdown(f"""
                <div style="padding: 4px 0; border-bottom: 1px solid #333;">
                    <span style="color: #858585;">[{timestamp}]</span>
                    <span style="color: {color};">[{event['type']}]</span>
                    <span style="color: #4ec9b0; font-weight: bold;">{direction}</span>: {event['content'][:60]}...
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.subheader("Summary")
        
        summary = st.session_state.tracker.get_activity_summary()
        
        st.metric("Total Events", summary['total_events'])
        st.metric("Active Agents", summary['active_agents'])
        st.metric("Missions", summary['missions_tracked'])
        
        st.divider()
        
        st.subheader("By Type")
        for event_type, count in sorted(summary['event_types'].items(), key=lambda x: x[1], reverse=True)[:5]:
            st.write(f"{event_type}: {count}")
        
        st.divider()
        
        st.subheader("Top Agents")
        for agent_id, count in summary['top_agents'][:5]:
            st.write(f"{agent_id}: {count}")

# ============== GROUP CHATS PAGE ==============
elif page == "💬 Group Chats":
    st.markdown('<p class="main-header">💬 Group Conversations</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2 = st.tabs(["Active Groups", "Create Group"])
    
    with tab1:
        st.subheader("Active Group Chats")
        
        groups = data.get('groups', [])
        
        if not groups:
            st.info("No active groups. Create one to enable multi-agent collaboration!")
        
        for group in groups:
            with st.expander(f"👥 {group['name']} ({group['member_count']} members)"):
                st.write(f"**Type:** {group['type']}")
                st.write(f"**Topic:** {group['topic'] or 'General'}")
                st.write(f"**Members:** {', '.join(group['members'])}")
                st.write(f"**Messages:** {group['message_count']}")
                
                # Show recent messages
                history = st.session_state.group_chat.get_group_history(group['id'], limit=10)
                if history:
                    st.markdown("**Recent Messages:**")
                    for msg in history:
                        st.markdown(f"<small><b>{msg['sender']}:</b> {msg['content'][:80]}...</small>", 
                                  unsafe_allow_html=True)
                
                # Send message to group
                message = st.text_input(f"Message to {group['name']}", key=f"msg_{group['id']}")
                if st.button("Send", key=f"send_{group['id']}"):
                    st.session_state.group_chat.send_to_group(
                        group_id=group['id'],
                        sender="user",
                        content=message
                    )
                    st.success("Sent!")
    
    with tab2:
        st.subheader("Create New Group Chat")
        
        agent_list = [a['name'] for a in data['agents']]
        
        group_name = st.text_input("Group Name")
        group_type = st.selectbox("Group Type", ["discussion", "workflow", "standup", "brainstorm", "review"])
        topic = st.text_input("Topic (optional)")
        members = st.multiselect("Select Members", agent_list)
        
        if st.button("👥 Create Group", type="primary"):
            if group_name and members:
                group = st.session_state.group_chat.create_group(
                    name=group_name,
                    members=members,
                    created_by="user",
                    chat_type=GroupChatType(group_type),
                    topic=topic
                )
                st.success(f"Created group: {group.id}")
                time.sleep(1)
                st.rerun()

# ============== HANDOFFS PAGE ==============
elif page == "🔄 Handoffs":
    st.markdown('<p class="main-header">🔄 Agent Handoffs</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["Recent Handoffs", "Create Handoff", "Auto-Handoff Suggestions"])
    
    with tab1:
        st.subheader("Recent Handoff Activity")
        
        handoffs = data.get('recent_handoffs', [])
        
        if not handoffs:
            st.info("No handoffs yet. Create one to see agents collaborate!")
        
        for handoff in handoffs:
            status_icon = {'pending': '⏳', 'accepted': '✅', 'rejected': '❌', 'completed': '✓', 'failed': '💥'}.get(handoff['status'], '?')
            
            with st.expander(f"{status_icon} {handoff.get('from_agent', 'Unknown')} → {handoff.get('to_agent', 'Unknown')} ({handoff['status']})"):
                st.write(f"**Reason:** {handoff.get('reason', 'No reason')}")
                if 'context' in handoff:
                    ctx = handoff['context']
                    st.write(f"**Original Task:** {ctx.get('original_task', 'Unknown')[:100]}...")
                    st.write(f"**Work Done:** {ctx.get('work_done', 'None')[:100]}...")
    
    with tab2:
        st.subheader("Create New Handoff")
        
        agent_list = [a['name'] for a in data['agents']]
        
        from_agent = st.selectbox("From Agent", agent_list)
        to_agent = st.selectbox("To Agent", [a for a in agent_list if a != from_agent])
        original_task = st.text_input("Original Task")
        work_done = st.text_area("Work Completed")
        next_steps = st.text_area("Next Steps (one per line)").split('\n')
        reason = st.text_input("Handoff Reason")
        
        if st.button("🔄 Initiate Handoff", type="primary"):
            from_id = next((a['id'] for a in data['agents'] if a['name'] == from_agent), None)
            to_id = next((a['id'] for a in data['agents'] if a['name'] == to_agent), None)
            
            if from_id and to_id:
                context = HandoffContext(
                    original_task=original_task,
                    work_done=work_done,
                    findings={},
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
    
    with tab3:
        st.subheader("Auto-Handoff Suggestions")
        st.info("Auto-handoff detects when agents should pass work based on task content and confidence.")
        
        # Show suggestion for a task
        if data['agents']:
            selected_agent = st.selectbox("Select Agent", [a['name'] for a in data['agents']])
            task_desc = st.text_area("Task Description to Analyze")
            
            if st.button("🔍 Analyze for Handoff"):
                agent_id = next((a['id'] for a in data['agents'] if a['name'] == selected_agent), None)
                if agent_id:
                    # Simulate a response for analysis
                    st.write("**Analysis would check for:**")
                    st.write("- Skill mismatches")
                    st.write("- Confidence indicators ('I'm not sure', etc.)")
                    st.write("- Completion phrases ('ready for next step')")
                    st.write("- Natural workflow transitions")

# ============== ALERTS PAGE ==============
elif page == "🔔 Alerts":
    st.markdown('<p class="main-header">🔔 Activity Alerts</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    tab1, tab2 = st.tabs(["Active Alerts", "Alert Rules"])
    
    with tab1:
        st.subheader("Active Alerts")
        
        alerts = data.get('active_alerts', [])
        
        if not alerts:
            st.success("✅ No active alerts! System is healthy.")
        
        for alert in alerts:
            severity_class = f"alert-{alert['severity']}"
            
            st.markdown(f"""
            <div class="{severity_class}">
                <h4>{alert['title']} ({alert['severity'].upper()})</h4>
                <p>{alert['message']}</p>
                <small>Source: {alert['source']} | {alert['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Acknowledge", key=f"ack_{alert['id']}"):
                st.session_state.alerts.acknowledge_alert(alert['id'], "user")
                st.success("Alert acknowledged!")
                time.sleep(1)
                st.rerun()
    
    with tab2:
        st.subheader("Alert Rules")
        
        rules = st.session_state.alerts.get_rules()
        
        for rule in rules:
            with st.expander(f"{rule['name']} ({'✓ Enabled' if rule['enabled'] else '✗ Disabled'})"):
                st.write(f"**Description:** {rule['description']}")
                st.write(f"**Severity:** {rule['severity']}")
                st.write(f"**Triggers:** {', '.join(rule['event_types'])}")
                st.write(f"**Channels:** {', '.join(rule['channels'])}")
                st.write(f"**Cooldown:** {rule['cooldown_minutes']} min")

# ============== ANALYTICS PAGE ==============
elif page == "📊 Analytics":
    st.markdown('<p class="main-header">📊 System Analytics</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    # System overview metrics
    metrics = data.get('system_metrics', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tasks", metrics.get('total_tasks', 0))
    with col2:
        st.metric("Success Rate", f"{metrics.get('success_rate', 0)}%")
    with col3:
        st.metric("Total Messages", metrics.get('total_messages', 0))
    with col4:
        st.metric("Total Handoffs", metrics.get('total_handoffs', 0))
    
    st.divider()
    
    # Agent Performance
    st.subheader("📈 Agent Performance")
    
    perf_data = data.get('agent_performance', [])
    if perf_data:
        # Create performance table
        perf_df = []
        for p in perf_data:
            perf_df.append({
                "Agent": p['agent_name'],
                "Completed": p['tasks_completed'],
                "Failed": p['tasks_failed'],
                "Success %": p['success_rate'],
                "Avg Time (s)": p['avg_task_time'],
                "Messages": p['messages_sent'] + p['messages_received'],
                "Handoffs": p['handoffs_initiated'] + p['handoffs_received']
            })
        
        st.dataframe(perf_df, use_container_width=True)
    
    st.divider()
    
    # Activity Timeline
    st.subheader("📊 Activity Timeline (24h)")
    
    timeline = data.get('activity_timeline', [])
    if timeline:
        # Prepare data for chart
        hours = [t['hour'] for t in timeline]
        messages = [t['messages'] for t in timeline]
        
        chart_data = {"Hour": hours, "Messages": messages}
        st.bar_chart(chart_data, x="Hour", y="Messages")

# ============== AGENTS PAGE ==============
elif page == "🤖 Agents":
    st.markdown('<p class="main-header">🤖 Agent Management</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Spawn Agents")
        available = data['available_agents']
        
        if available:
            selected = st.multiselect("Select agents", available)
            
            if st.button("🚀 Spawn Selected", type="primary"):
                for agent_name in selected:
                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                    if result:
                        st.success(f"Spawned {agent_name}")
                time.sleep(1)
                st.rerun()
    
    with col2:
        st.subheader("⚡ Quick Squads")
        
        squads = {
            "🎯 Sales Squad": ['hunter', 'pepper', 'sage'],
            "🎨 Creative Squad": ['quill', 'pixel', 'pepper'],
            "💻 Dev Squad": ['code', 'guardian', 'wong'],
            "🔬 Research Squad": ['scout', 'sage', 'shuri']
        }
        
        for squad_name, members in squads.items():
            if st.button(f"Spawn {squad_name}"):
                for name in members:
                    st.session_state.orchestrator.spawn_agent(name)
                st.success(f"{squad_name} spawned!")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    
    # Agent details
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

# ============== MISSIONS PAGE ==============
elif page == "📋 Missions":
    st.markdown('<p class="main-header">📋 Mission Control</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
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
            
            # Mission activity
            st.subheader("Activity Log")
            mission_activity = st.session_state.tracker.get_mission_activity(mission.id)
            
            if mission_activity:
                for event in mission_activity[-20:]:
                    st.write(f"[{event['type']}] {event['from_agent']}: {event['content'][:80]}...")
            
            # Tasks
            st.subheader("Tasks")
            for task in mission.tasks:
                status_icon = {"pending": "⏳", "in_progress": "🔵", "completed": "✅", "failed": "❌"}.get(task.status, "⏳")
                
                with st.expander(f"{status_icon} {task.description[:60]}..."):
                    st.write(f"**Status:** {task.status}")
                    st.write(f"**Assigned to:** {task.assigned_to or 'Unassigned'}")
                    
                    if task.result:
                        st.code(task.result[:500])
                    
                    if task.status == "pending":
                        agent_list = [a['name'] for a in data['agents'] if a['status'] == 'idle']
                        if agent_list:
                            assign_to = st.selectbox(f"Assign to", agent_list, key=f"assign_{task.id}")
                            if st.button("Execute", key=f"exec_{task.id}"):
                                st.session_state.orchestrator.assign_task(assign_to, task.description, mission.id)
                                st.success(f"Assigned to {assign_to}")
    else:
        st.info("No missions. Create one in '➕ Create Mission' tab.")

# ============== CREATE MISSION PAGE ==============
elif page == "➕ Create Mission":
    st.markdown('<p class="main-header">🚀 Create New Mission</p>', unsafe_allow_html=True)
    
    data = get_dashboard_data()
    if not data:
        st.stop()
    
    with st.form("mission_form"):
        title = st.text_input("Mission Title")
        description = st.text_area("Description")
        
        # Auto-handoff suggestion
        st.subheader("🤖 Auto-Handoff Suggestion")
        if st.checkbox("Suggest agent workflow"):
            available_agents = [a['name'] for a in data['agents']] if data['agents'] else []
            suggested_chain = st.session_state.orchestrator.auto_handoff.suggest_handoff_chain(
                description, available_agents
            )
            
            if suggested_chain:
                st.write("**Suggested Workflow:**")
                for i, step in enumerate(suggested_chain, 1):
                    st.write(f"{i}. {step['agent'].title()}")
        
        st.subheader("Tasks")
        tasks = []
        for i in range(5):
            col1, col2 = st.columns([3, 1])
            with col1:
                task_desc = st.text_input(f"Task {i+1}", key=f"task_{i}")
            with col2:
                available_agents = [a['name'] for a in data['agents']] if data['agents'] else []
                assigned = st.selectbox(f"Agent", ["Auto"] + available_agents, key=f"agent_{i}")
            
            if task_desc:
                tasks.append({"description": task_desc, "assigned_to": None if assigned == "Auto" else assigned})
        
        submitted = st.form_submit_button("🚀 Launch Mission", type="primary")
        
        if submitted and title and tasks:
            mission = st.session_state.orchestrator.create_mission(
                title=title, description=description, tasks=tasks
            )
            
            # Optionally create a group chat for this mission
            if st.checkbox("Create group chat for this mission"):
                agent_names = [t['assigned_to'] for t in tasks if t['assigned_to']]
                if agent_names:
                    st.session_state.group_chat.create_workflow_group(
                        mission_id=mission.id,
                        mission_title=title,
                        agents=agent_names
                    )
            
            st.success(f"Mission created: {mission.id}")

# ============== SYSTEM PAGE ==============
elif page == "⚙️ System":
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
    
    # Version info
    st.divider()
    st.subheader("📦 Version Information")
    st.write("**Workspace Version:** v1.1.0")
    st.write("**Last Updated:** 2026-03-07")
    st.write("**GitHub:** https://github.com/bilyfoster/workspace")

# Version Footer (always shown)
st.sidebar.divider()
st.sidebar.markdown("---")
footer_text = "**Workspace v1.1.0** 🎯  \nRunning on Herbie  \n" + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.sidebar.markdown(footer_text)

# Fixed footer with version
version_footer = """
<div class="version-footer">
    <b>Workspace v1.1.0</b> | Built for Herbie | 
    <a href="https://github.com/bilyfoster/workspace" target="_blank">GitHub</a>
</div>
"""
st.markdown(version_footer, unsafe_allow_html=True)
