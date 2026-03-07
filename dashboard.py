#!/usr/bin/env python3
"""
Workspace Dashboard v1.6.2 - Fixed HUD + Logs

Usage:
    streamlit run dashboard.py

Version: v1.6.2
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
    page_title="Workspace | v1.6.2",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 1rem;
    }
    
    /* HUD Styles */
    .hud-box {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }
    
    .hud-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    
    .hud-title {
        color: #667eea;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .hud-metrics {
        display: flex;
        gap: 20px;
    }
    
    .hud-metric {
        text-align: center;
        color: white;
    }
    
    .hud-metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .hud-metric-value.working {
        color: #ffc107;
    }
    
    .hud-metric-value.alert {
        color: #ff4757;
    }
    
    .hud-metric-label {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
    }
    
    /* Agent Grid */
    .agent-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
        gap: 10px;
        margin-top: 12px;
    }
    
    /* Chat Styles */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    
    .chat-bubble-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px auto;
        max-width: 70%;
    }
    
    .chat-bubble-agent {
        background: #f0f2f5;
        color: #1a1a1a;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px auto 8px 0;
        max-width: 70%;
        border: 1px solid #e0e0e0;
    }
    
    .chat-header {
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 4px;
        opacity: 0.9;
    }
    
    /* Status Indicators */
    .status-idle { color: #28a745; }
    .status-working { color: #ffc107; animation: blink 1s infinite; }
    .status-error { color: #dc3545; }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Log styles */
    .log-entry {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        padding: 4px 8px;
        border-left: 3px solid transparent;
        margin: 2px 0;
    }
    
    .log-info { border-left-color: #17a2b8; background: #e3f2fd; }
    .log-success { border-left-color: #28a745; background: #e8f5e9; }
    .log-warning { border-left-color: #ffc107; background: #fff3cd; }
    .log-error { border-left-color: #dc3545; background: #ffebee; }
    
    /* Mission card */
    .mission-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .progress-bar {
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s;
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
if 'explicit_handoff' not in st.session_state:
    from shared.explicit_handoff import get_explicit_handoff_manager
    st.session_state.explicit_handoff = get_explicit_handoff_manager(st.session_state.orchestrator)
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'page' not in st.session_state:
    st.session_state.page = "dashboard"
if 'thinking' not in st.session_state:
    st.session_state.thinking = False
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None
if 'logs' not in st.session_state:
    st.session_state.logs = []

def get_data():
    """Get current system state"""
    try:
        return st.session_state.orchestrator.get_dashboard_data()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def add_log(level: str, message: str):
    """Add a log entry"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append({
        "time": timestamp,
        "level": level,
        "message": message
    })
    # Keep last 100 logs
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

def render_hud():
    """Render the HUD panel - simplified clean version"""
    data = get_data()
    if not data:
        return
    
    agents = data['agents']
    working = len([a for a in agents if a['status'] == 'working'])
    errors = len([a for a in agents if a['status'] == 'error'])
    missions = len([m for m in data['missions'] if m['status'] == 'active'])
    tasks = sum(a['tasks_completed'] for a in agents)
    
    # Get health summary
    health = data.get('health_summary', {})
    stuck = health.get('stuck', 0)
    
    # Show Manager Pulse messages (proactive updates)
    manager_running = any(a['name'] == 'Manager' for a in agents)
    if manager_running:
        # Get pulse events from orchestrator
        pulse = st.session_state.orchestrator.manager_pulse
        if pulse:
            recent_events = pulse.get_recent_events(3)
            if recent_events:
                with st.container():
                    st.markdown("#### 💓 Manager Pulse")
                    for event in reversed(recent_events):
                        icon = "ℹ️" if event.severity == "info" else "⚠️" if event.severity == "warning" else "🔴"
                        st.info(f"{icon} {event.message}")
    
    # Show health alerts banner if there are issues
    if errors > 0 or stuck > 0:
        alert_msg = []
        if errors > 0:
            alert_msg.append(f"{errors} agent(s) in error state")
        if stuck > 0:
            alert_msg.append(f"{stuck} agent(s) stuck")
        st.error(f"⚠️ Health Alert: {', '.join(alert_msg)}. Check Logs & Debug for details.")
    
    # HUD Header with metrics
    st.subheader("🎯 Workspace HUD")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Agents", len(agents))
    with col2:
        st.metric("Working", working)
    with col3:
        alert_delta = f"🔴 {errors}" if errors > 0 else None
        st.metric("Alerts", errors, delta=alert_delta, delta_color="inverse")
    with col4:
        st.metric("Missions", missions)
    with col5:
        st.metric("Tasks", tasks)
    
    st.divider()
    
    # Agent cards row
    if agents:
        st.write("**Click an agent to chat:**")
        cols = st.columns(min(len(agents), 6))
        for idx, agent in enumerate(agents):
            with cols[idx % 6]:
                # Get health state for this agent
                agent_health = health.get('agents', {}).get(agent['id'], {})
                health_state = agent_health.get('state', 'idle')
                
                # Build status line
                if health_state == 'error' or agent['status'] == 'error':
                    status_icon = "🔴 ERROR"
                    btn_type = "primary"
                elif health_state == 'stuck':
                    status_icon = "⏱️ STUCK"
                    btn_type = "primary"
                elif agent['status'] == 'working':
                    status_icon = "⚡ Working"
                    btn_type = "primary"
                else:
                    status_icon = "☕ Idle"
                    btn_type = "secondary"
                
                task_preview = agent.get('current_task', '')[:12] + "..." if agent.get('current_task') else "Ready"
                
                btn_label = f"**{agent['avatar']} {agent['name']}**  \n{status_icon}  \n_{task_preview}_"
                
                if st.button(btn_label, key=f"hud_agent_{agent['id']}", use_container_width=True, type=btn_type):
                    st.session_state.selected_agent = agent
                    add_log("info", f"Selected agent: {agent['name']}")
                    st.rerun()
    else:
        st.info("🤖 No agents active. Use sidebar to spawn agents.")

def render_dashboard():
    """Main dashboard with chat"""
    
    # Show selected agent context
    if st.session_state.selected_agent:
        agent = st.session_state.selected_agent
        col1, col2 = st.columns([6, 1])
        with col1:
            st.info(f"💬 Chatting with {agent['avatar']} **{agent['name']}** ({agent['status']})")
        with col2:
            if st.button("✕ Clear Selection", use_container_width=True):
                st.session_state.selected_agent = None
                st.rerun()
    else:
        st.info("💡 Tip: Click an agent in the HUD above to chat directly, or type below to message the Manager")
    
    # Chat container
    st.markdown("---")
    
    # Custom chat display (no st.chat_message to avoid default avatars)
    chat_html = []
    chat_html.append("<div style='max-width: 800px; margin: 0 auto;'>")
    
    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            # User message - right aligned, blue
            chat_html.append(f"""
            <div style='display: flex; justify-content: flex-end; margin: 12px 0;'>
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 12px 16px; border-radius: 18px 18px 4px 18px; 
                           max-width: 70%; box-shadow: 0 2px 8px rgba(102,126,234,0.3);'>
                    <div style='font-size: 0.8em; opacity: 0.9; margin-bottom: 4px;'>You</div>
                    {msg['content']}
                </div>
            </div>
            """)
        else:
            # Agent message - left aligned, gray
            avatar = msg.get('avatar', '🤖')
            name = msg.get('name', 'Agent')
            chat_html.append(f"""
            <div style='display: flex; justify-content: flex-start; margin: 12px 0;'>
                <div style='background: #f8f9fa; border: 1px solid #e9ecef; 
                           color: #212529; padding: 12px 16px; border-radius: 18px 18px 18px 4px; 
                           max-width: 70%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <div style='font-size: 0.8em; color: #667eea; margin-bottom: 4px;'>
                        {avatar} {name}
                    </div>
                    {msg['content']}
                </div>
            </div>
            """)
    
    # Thinking indicator with moon phases
    if st.session_state.thinking:
        chat_html.append("""
        <div style='display: flex; justify-content: flex-start; margin: 12px 0;'>
            <div style='background: #e3f2fd; border: 2px solid #2196f3; 
                       color: #1565c0; padding: 12px 20px; border-radius: 18px; 
                       box-shadow: 0 2px 8px rgba(33,150,243,0.2);
                       display: flex; align-items: center; gap: 10px;'>
                <span>Processing</span>
                <span class='thinking-dot'></span>
                <span class='thinking-dot'></span>
                <span class='thinking-dot'></span>
            </div>
        </div>
        <style>
            @keyframes pulse-dot {
                0%, 100% { opacity: 0.3; transform: scale(0.8); }
                50% { opacity: 1; transform: scale(1.2); }
            }
            .thinking-dot {
                animation: pulse-dot 1.5s infinite;
                display: inline-block;
                width: 8px;
                height: 8px;
                background: #2196f3;
                border-radius: 50%;
                margin: 0 3px;
            }
            .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
            .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
        </style>
        """)
    
    chat_html.append("</div>")
    st.markdown("".join(chat_html), unsafe_allow_html=True)
    
    # Input
    message = st.chat_input("Message your team...")
    if message:
        process_message(message)

def process_message(message: str):
    """Process user message"""
    if not message.strip():
        return
    
    st.session_state.messages.append({"role": "user", "content": message})
    st.session_state.thinking = True
    add_log("info", f"User message: {message[:50]}...")
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
            "role": "agent", "name": "System", "avatar": "⚠️",
            "content": "Error connecting to system"
        })
        add_log("error", "Failed to connect to system")
        st.session_state.thinking = False
        st.rerun()
        return
    
    msg_lower = last_msg.lower()
    
    # Check for specific agent mention
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
            summary += f"{status_icon} **{a['name']}** ({a['status']}){task}\n"
        summary += f"\n📊 Total tasks completed: {sum(a['tasks_completed'] for a in data['agents'])}"
        
        st.session_state.messages.append({
            "role": "agent", "name": "Manager", "avatar": "🎩", "content": summary
        })
        add_log("success", "Generated team status summary")
    
    elif "spawn" in msg_lower or "start" in msg_lower:
        spawned = []
        for name in data.get('available_agents', []):
            if name.lower() in msg_lower:
                add_log("info", f"Spawning agent: {name}")
                result = st.session_state.orchestrator.spawn_agent(name)
                if result:
                    resource_monitor.register_agent(result.id, result.name)
                    spawned.append(name.title())
                    add_log("success", f"Spawned {name}")
        
        if spawned:
            st.session_state.messages.append({
                "role": "agent", "name": "Manager", "avatar": "🎩",
                "content": f"✅ Spawned: {', '.join(spawned)}"
            })
        else:
            available = ", ".join(data.get('available_agents', []))
            st.session_state.messages.append({
                "role": "agent", "name": "Manager", "avatar": "🎩",
                "content": f"I didn't find agents to spawn. Available: {available}"
            })
    
    elif target_agent or st.session_state.selected_agent:
        agent = target_agent or st.session_state.selected_agent
        add_log("info", f"Chatting with {agent['name']}: {last_msg[:50]}...")
        
        # Get response (thinking indicator is shown in chat UI)
        response = st.session_state.orchestrator.chat_with_agent_sync(
            agent['name'], last_msg, timeout=30
        )
        
        if response:
            st.session_state.messages.append({
                "role": "agent", "name": agent['name'], "avatar": agent['avatar'], "content": response
            })
            add_log("success", f"{agent['name']} responded")
        else:
            st.session_state.messages.append({
                "role": "agent", "name": agent['name'], "avatar": agent['avatar'],
                "content": "❌ I'm not responding. Try respawning me from Agent Control."
            })
            add_log("error", f"{agent['name']} did not respond")
    
    else:
        # Default to Manager
        manager = next((a for a in data['agents'] if a['name'] == 'Manager'), None)
        target = manager or (data['agents'][0] if data['agents'] else None)
        
        if target:
            add_log("info", f"Sending to {target['name']}: {last_msg[:50]}...")
            # Get response (thinking indicator is shown in chat UI)
            # Use longer timeout for Manager with context
            timeout = 60 if target['name'] == 'Manager' else 30
            
            # Show that we're sending
            add_log("info", f"Waiting up to {timeout}s for response...")
            
            response = st.session_state.orchestrator.chat_with_agent_sync(
                target['name'], last_msg, timeout=timeout
            )
            
            if response:
                st.session_state.messages.append({
                    "role": "agent", "name": target['name'], "avatar": target['avatar'], "content": response
                })
                add_log("success", f"{target['name']} responded ({len(response)} chars)")
            else:
                # More specific error message
                error_msg = f"❌ {target['name']} did not respond within {timeout}s. "
                if target['status'] != 'idle':
                    error_msg += f"Agent status is '{target['status']}'. "
                error_msg += "Check Logs & Debug for details."
                
                st.session_state.messages.append({
                    "role": "agent", "name": "System", "avatar": "⚠️",
                    "content": error_msg
                })
                add_log("error", f"{target['name']} timeout/no response after {timeout}s")
        else:
            st.session_state.messages.append({
                "role": "agent", "name": "System", "avatar": "🤖",
                "content": f"No agents available. Found {len(data['agents'])} agents but none suitable. Spawn Manager first!"
            })
            add_log("warning", f"No suitable agents. Total: {len(data['agents'])}")
    
    st.session_state.thinking = False
    st.rerun()

def render_agent_control():
    """Agent management page"""
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    
    st.header("🤖 Agent Control")
    
    data = get_data()
    if not data:
        return
    
    # Tabs
    tabs = st.tabs(["Active Agents", "Spawn Agents", "Create New"])
    
    with tabs[0]:
        if not data['agents']:
            st.info("No agents running")
        else:
            # Get health data
            health = data.get('health_summary', {})
            health_agents = health.get('agents', {})
            
            st.write(f"**{len(data['agents'])} agents active**")
            
            # Show health issues summary
            stuck_agents = [aid for aid, h in health_agents.items() if h.get('state') == 'stuck']
            error_agents = [aid for aid, h in health_agents.items() if h.get('state') == 'error']
            
            if stuck_agents or error_agents:
                st.warning(f"⚠️ Health Issues: {len(stuck_agents)} stuck, {len(error_agents)} errors")
            
            for agent in data['agents']:
                agent_health = health_agents.get(agent['id'], {})
                health_state = agent_health.get('state', 'unknown')
                
                # Show health state in header
                status_display = agent['status']
                if health_state == 'stuck':
                    status_display += " ⏱️ STUCK"
                elif health_state == 'error':
                    status_display += " 🔴 ERROR"
                
                with st.expander(f"{agent['avatar']} {agent['name']} - {status_display}"):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**ID:** {agent['id']}")
                        st.write(f"**Role:** {agent['role']}")
                        st.write(f"**Health State:** `{health_state}`")
                        st.write(f"**Tasks Completed:** {agent['tasks_completed']}")
                        if agent.get('current_task'):
                            st.write(f"**Current Task:** {agent['current_task']}")
                            # Show task duration if working
                            if agent['status'] == 'working':
                                st.write(f"**Time in State:** {agent_health.get('time_in_state', 'unknown')}")
                        st.write(f"**Thread Alive:** {'Yes' if agent.get('thread_alive') else 'No'}")
                        if agent_health.get('consecutive_errors', 0) > 0:
                            st.error(f"**Consecutive Errors:** {agent_health['consecutive_errors']}")
                        if agent_health.get('total_restarts', 0) > 0:
                            st.info(f"**Total Restarts:** {agent_health['total_restarts']}")
                    with col2:
                        if st.button("🔄 Respawn", key=f"respawn_{agent['id']}"):
                            add_log("info", f"Respawning {agent['name']}")
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            time.sleep(0.5)
                            result = st.session_state.orchestrator.spawn_agent(agent['name'].lower())
                            if result:
                                resource_monitor.register_agent(result.id, result.name)
                                add_log("success", f"Respawned {agent['name']}")
                            st.rerun()
                        
                        # Troubleshoot button for problematic agents
                        if health_state in ['error', 'stuck']:
                            if st.button("🔧 Troubleshoot", key=f"troubleshoot_{agent['id']}"):
                                add_log("info", f"Troubleshooting {agent['name']}")
                                st.info(f"🛠️ Troubleshooting {agent['name']}...")
                                st.write("**Diagnostic Steps:**")
                                st.write("1. ✓ Check thread status")
                                st.write(f"   - Thread alive: {agent.get('thread_alive', False)}")
                                st.write("2. ✓ Review health state")
                                st.write(f"   - State: {health_state}")
                                st.write(f"   - Errors: {agent_health.get('consecutive_errors', 0)}")
                                st.write("3. → Recommended action: Respawn")
                    with col3:
                        if st.button("🛑 Kill", key=f"kill_{agent['id']}"):
                            add_log("info", f"Killing {agent['name']}")
                            st.session_state.orchestrator.kill_agent(agent['id'])
                            resource_monitor.unregister_agent(agent['id'])
                            add_log("warning", f"Killed {agent['name']}")
                            st.rerun()
    
    with tabs[1]:
        st.subheader("Spawn Individual Agents")
        available = data.get('available_agents', [])
        
        if available:
            cols = st.columns(4)
            for idx, name in enumerate(available):
                with cols[idx % 4]:
                    is_running = any(a['name'].lower() == name.lower() for a in data['agents'])
                    if is_running:
                        st.success(f"✅ {name.title()}")
                    else:
                        if st.button(f"🚀 Spawn {name.title()}", key=f"spawn_{name}"):
                            add_log("info", f"Spawning {name}")
                            result = st.session_state.orchestrator.spawn_agent(name)
                            if result:
                                resource_monitor.register_agent(result.id, result.name)
                                add_log("success", f"Spawned {name}")
                            st.rerun()
        else:
            st.error("No agent souls found!")
        
        st.divider()
        st.subheader("Quick Squads")
        
        squads = {
            "🎯 Sales Squad": ['hunter', 'pepper', 'sage'],
            "🎨 Creative Squad": ['quill', 'pixel', 'shuri'],
            "💻 Dev Squad": ['code', 'guardian', 'wong'],
            "🔬 Research Squad": ['scout', 'sage', 'shuri']
        }
        
        for squad_name, agents in squads.items():
            if st.button(f"Spawn {squad_name}", key=f"squad_{squad_name}"):
                add_log("info", f"Spawning {squad_name}")
                for agent_name in agents:
                    result = st.session_state.orchestrator.spawn_agent(agent_name)
                    if result:
                        resource_monitor.register_agent(result.id, result.name)
                add_log("success", f"Spawned {squad_name}")
                st.rerun()
    
    with tabs[2]:
        st.subheader("Create Custom Agent")
        
        templates = agent_factory.list_templates()
        st.write("**From Template:**")
        
        for key, label in templates.items():
            with st.expander(label):
                name = st.text_input("Agent Name", key=f"template_name_{key}")
                if st.button("Create & Spawn", key=f"template_create_{key}"):
                    if name:
                        add_log("info", f"Creating agent from template: {key}")
                        soul_path = agent_factory.create_agent_from_template(key, name)
                        if soul_path:
                            result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                            if result:
                                resource_monitor.register_agent(result.id, result.name)
                                add_log("success", f"Created and spawned {name}")
                            st.rerun()
        
        st.divider()
        st.write("**Fully Custom:**")
        
        with st.form("custom_agent"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *")
                role = st.text_input("Role *")
                avatar = st.text_input("Avatar (emoji)", value="🤖")
            with col2:
                model = st.selectbox("Model", ["qwen3.5:9b", "dolphin3", "gemma3", "qwen3-coder"])
                temp = st.slider("Temperature", 0.0, 1.0, 0.7)
            
            essence = st.text_area("Essence/Personality *")
            skills = st.text_area("Skills (one per line) *")
            
            if st.form_submit_button("✨ Create & Spawn"):
                if all([name, role, essence, skills]):
                    add_log("info", f"Creating custom agent: {name}")
                    skill_list = [s.strip() for s in skills.split('\n') if s.strip()]
                    soul_path = agent_factory.create_custom_agent(
                        name=name, role=role, avatar=avatar, essence=essence,
                        skills=skill_list, model=model, temperature=temp
                    )
                    if soul_path:
                        result = st.session_state.orchestrator.spawn_agent(soul_path.parent.name)
                        if result:
                            resource_monitor.register_agent(result.id, result.name)
                            add_log("success", f"Created and spawned {name}")
                        st.rerun()

def render_missions():
    """Missions page with execution visibility"""
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    
    st.header("📋 Mission Control")
    
    data = get_data()
    if not data:
        return
    
    # Show running executions
    running = st.session_state.orchestrator.get_running_executions()
    if running:
        st.warning(f"⏳ {len(running)} mission(s) currently executing")
        for mission_id in running:
            st.write(f"- {mission_id}")
    
    st.divider()
    
    # List missions
    missions = data.get('missions', [])
    
    if not missions:
        st.info("No missions yet. Create one below!")
    else:
        st.subheader(f"Active Missions ({len(missions)})")
        
        for mission in missions:
            with st.expander(f"📋 {mission['title']} - {mission['progress']['percent']}%"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Status:** {mission['status']}")
                with col2:
                    st.write(f"**Progress:** {mission['progress']['completed']}/{mission['progress']['total']}")
                with col3:
                    st.write(f"**Tasks:** {mission['tasks']}")
                
                # Progress bar
                st.progress(mission['progress']['percent'] / 100)
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if mission['status'] == 'active' and mission['progress']['percent'] < 100:
                        if st.button("🚀 Execute Mission", key=f"exec_{mission['id']}"):
                            add_log("info", f"Executing mission: {mission['title']}")
                            st.session_state.orchestrator.execute_mission_auto(mission['id'])
                            st.success("✅ Execution started! Check logs for progress.")
                            add_log("success", f"Started execution of {mission['title']}")
                            time.sleep(1)
                            st.rerun()
                
                with col2:
                    if st.button("📥 Export Results", key=f"export_{mission['id']}"):
                        export_path = st.session_state.orchestrator.export_mission(mission['id'], "markdown")
                        if export_path:
                            st.success(f"✅ Exported to: {export_path}")
                            add_log("success", f"Exported mission to {export_path}")
                        else:
                            st.error("❌ Export failed")
                
                # Show tasks
                full_mission = st.session_state.orchestrator.mission_manager.get_mission(mission['id'])
                if full_mission:
                    st.write("**Tasks:**")
                    for task in full_mission.tasks:
                        status_icon = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}.get(task.status, "⏳")
                        st.write(f"{status_icon} {task.description} → {task.assigned_to or 'Unassigned'}")
                        if task.result:
                            with st.expander("View Result"):
                                st.text(task.result[:500])
    
    st.divider()
    
    # Create new mission
    st.subheader("➕ Create New Mission")
    
    with st.form("new_mission"):
        title = st.text_input("Mission Title *")
        desc = st.text_area("Description")
        
        st.write("**Tasks:**")
        tasks = []
        for i in range(5):
            cols = st.columns([3, 2])
            with cols[0]:
                task_desc = st.text_input(f"Task {i+1}", key=f"task_{i}")
            with cols[1]:
                agent_options = ["Auto"] + [a['name'] for a in data['agents']]
                assigned = st.selectbox(f"Assign to", agent_options, key=f"assign_{i}")
            if task_desc:
                tasks.append({
                    "description": task_desc,
                    "assigned_to": None if assigned == "Auto" else assigned
                })
        
        if st.form_submit_button("🚀 Create Mission"):
            if title and tasks:
                add_log("info", f"Creating mission: {title}")
                mission = st.session_state.orchestrator.create_mission(
                    title=title, description=desc, tasks=tasks
                )
                add_log("success", f"Created mission: {mission.id}")
                st.success(f"✅ Mission created: {mission.id}")
                time.sleep(1)
                st.rerun()

def render_logs():
    """Logs and debug page"""
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    
    st.header("📜 Logs & Debug")
    
    # System status
    data = get_data()
    if data:
        # Health summary
        health = data.get('health_summary', {})
        
        st.subheader("🏥 Health Status")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total", health.get('total_agents', 0))
        with col2:
            st.metric("Healthy", health.get('healthy', 0))
        with col3:
            st.metric("Working", health.get('working', 0))
        with col4:
            stuck = health.get('stuck', 0)
            st.metric("Stuck", stuck, delta=f"⚠️ {stuck}" if stuck > 0 else None, delta_color="inverse")
        with col5:
            errors = health.get('error', 0)
            st.metric("Errors", errors, delta=f"🔴 {errors}" if errors > 0 else None, delta_color="inverse")
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Agents", len(data['agents']))
        with col2:
            st.metric("Messages", len(st.session_state.logs))
        with col3:
            sys_res = resource_monitor.get_system_summary()
            st.metric("Memory %", f"{sys_res.get('system_memory_percent', 0):.1f}%")
    
    st.divider()
    
    # Log filter
    col1, col2 = st.columns([1, 3])
    with col1:
        log_filter = st.selectbox("Filter", ["All", "Info", "Success", "Warning", "Error"])
    with col2:
        if st.button("🧹 Clear Logs"):
            st.session_state.logs = []
            st.rerun()
    
    # Display logs
    st.subheader("Recent Activity")
    
    logs_to_show = st.session_state.logs
    if log_filter != "All":
        level_map = {"Info": "info", "Success": "success", "Warning": "warning", "Error": "error"}
        logs_to_show = [l for l in logs_to_show if l['level'] == level_map.get(log_filter, "info")]
    
    if not logs_to_show:
        st.info("No logs yet. Activity will appear here.")
    else:
        for log in reversed(logs_to_show[-50:]):  # Show last 50
            css_class = f"log-{log['level']}"
            st.markdown(f"""
            <div class="log-entry {css_class}">
                <strong>[{log['time']}]</strong> {log['message']}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Debug info
    st.subheader("Debug Information")
    
    if data:
        with st.expander("Agent Details"):
            for agent in data['agents']:
                st.json({
                    "id": agent['id'],
                    "name": agent['name'],
                    "status": agent['status'],
                    "thread_alive": agent.get('thread_alive'),
                    "tasks_completed": agent['tasks_completed']
                })
        
        with st.expander("System Resources"):
            sys_res = resource_monitor.get_system_summary()
            st.json(sys_res)
        
        with st.expander("Message Bus"):
            bus = st.session_state.orchestrator.bus
            st.write(f"Registered queues: {len(bus._agent_queues)}")
            st.write(f"Message history: {len(bus._message_history)}")

def render_handoffs():
    """Explicit handoffs page (Swarm-style)"""
    if st.button("← Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    
    st.header("🔄 Explicit Handoffs")
    st.markdown("Swarm-style function-based agent handoffs")
    
    handoff_mgr = st.session_state.explicit_handoff
    
    # Pending handoffs
    st.subheader("⏳ Pending Handoffs")
    pending = handoff_mgr.get_pending()
    if pending:
        for h in pending:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{h.from_agent}** → **{h.to_agent}**")
                st.caption(f"Type: {h.handoff_type.value}")
                if h.context.get('task'):
                    st.write(f"Task: {h.context['task'][:50]}...")
            with col2:
                if st.button("✅ Execute", key=f"exec_{h.id}"):
                    handoff_mgr.execute_handoff(h.id)
                    st.success("Executed!")
                    st.rerun()
            with col3:
                if st.button("❌ Reject", key=f"reject_{h.id}"):
                    handoff_mgr.reject_handoff(h.id)
                    st.rerun()
    else:
        st.info("No pending handoffs")
    
    st.divider()
    
    # Recent handoffs
    st.subheader("📜 Recent Handoffs")
    recent = handoff_mgr.get_recent(10)
    if recent:
        for h in reversed(recent):
            icon = "✅" if h.status == "completed" else "❌" if h.status == "rejected" else "⏳"
            st.write(f"{icon} {h.from_agent} → {h.to_agent} ({h.status})")
    else:
        st.info("No handoffs yet")
    
    st.divider()
    
    # How to use
    with st.expander("How to Use Explicit Handoffs"):
        st.markdown("""
        Agents can trigger handoffs by including specific patterns in their responses:
        
        **Patterns detected:**
        - `[handoff:agent_name]` - Explicit handoff tag
        - `[transfer to agent_name]` - Alternative syntax
        - "handoff to agent_name" - Natural language
        
        **Example:**
        ```
        I've completed the design mockup. [handoff:code] 
        Code can now implement the frontend.
        ```
        
        This will:
        1. Detect the handoff request
        2. Spawn Code if not running
        3. Pass context to Code
        4. Notify both agents
        
        **vs Manager Orchestration:**
        - **Explicit handoffs**: Agents decide when to transfer (Swarm-style)
        - **Manager orchestration**: Manager decides who does what (our style)
        
        Both work together - use whichever fits your workflow!
        """)

# ==================== MAIN APP ====================

# Debug: Log current state
if st.session_state.get('debug_mode'):
    st.write(f"DEBUG: thinking={st.session_state.thinking}, agents={len(get_data().get('agents', [])) if get_data() else 0}")

# Process thinking - show inline indicator
if st.session_state.thinking:
    st.info("⏳ Processing your message...")
    generate_response()

# Always show HUD at top
render_hud()

st.markdown("---")

# Sidebar navigation
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
    
    if st.button("📜 Logs & Debug", use_container_width=True):
        st.session_state.page = "logs"
        st.rerun()
    
    if st.button("🔄 Handoffs", use_container_width=True):
        st.session_state.page = "handoffs"
        st.rerun()
    
    st.markdown("---")
    
    if st.button("🚀 Spawn Manager", use_container_width=True):
        add_log("info", "Spawning Manager")
        result = st.session_state.orchestrator.spawn_agent('manager')
        if result:
            resource_monitor.register_agent(result.id, result.name)
            add_log("success", "Manager spawned")
        st.rerun()
    
    st.markdown("---")
    st.caption(f"Workspace v1.6.2")

# Render main content
if st.session_state.page == "dashboard":
    render_dashboard()
elif st.session_state.page == "agents":
    render_agent_control()
elif st.session_state.page == "missions":
    render_missions()
elif st.session_state.page == "logs":
    render_logs()
elif st.session_state.page == "handoffs":
    render_handoffs()
