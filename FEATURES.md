# Workspace Features

## 🎯 Activity Monitoring & Agent Handoffs

Workspace now provides complete visibility into agent activity and enables seamless collaboration between agents.

---

## 📡 Activity Monitoring

### What's Tracked

Every action in the system is logged:

| Event Type | Description | Example |
|------------|-------------|---------|
| `agent_online` | Agent process started | "Hunter came online" |
| `agent_offline` | Agent process stopped | "Agent went offline" |
| `agent_message` | Agent-to-agent message | "Hunter → Pepper: Campaign draft ready" |
| `user_message` | User to agent | "User → Hunter: Review this list" |
| `task_assigned` | Task given to agent | "Task assigned: Write 5 emails" |
| `task_started` | Agent began working | "Task started: Research prospects" |
| `task_completed` | Agent finished | "Task completed: ✓ 5 emails written" |
| `task_failed` | Task error | "Task failed: API timeout" |
| `handoff_request` | Agent A asks to handoff to B | "Handoff request: Email sequence" |
| `handoff_accept` | Agent B accepts | "Handoff accepted by Pepper" |
| `handoff_reject` | Agent B declines | "Handoff rejected: Busy" |
| `mission_created` | New mission started | "Mission created: Q2 Campaign" |
| `mission_completed` | Mission finished | "Mission completed: Launch" |

### Dashboard Views

1. **Activity Feed 🔥** - Real-time log (like a terminal)
2. **Agent Chat 💬** - Conversation view between specific agents
3. **Mission Activity** - All events for a specific mission

---

## 🔄 Agent-to-Agent Handoffs

### What Are Handoffs?

Handoffs allow agents to collaborate on complex tasks:

```
Mission: Launch Marketing Campaign

Phase 1: Scout researches target audience
    ↓ [HANDOFF]
Phase 2: Hunter writes cold emails based on research
    ↓ [HANDOFF]
Phase 3: Pepper sets up email automation
    ↓ [HANDOFF]
Phase 4: Sage analyzes results
```

### Handoff Information Passed

When Agent A hands off to Agent B:

```yaml
handoff:
  from_agent: "scout"
  to_agent: "hunter"
  context:
    original_task: "Research target audience for SaaS product"
    work_done: "Analyzed 50 companies, identified 3 ideal personas"
    findings:
      - "Persona 1: CTOs at 50-200 person companies"
      - "Persona 2: VP Engineering at startups"
      - "Key pain: CI/CD pipeline complexity"
    next_steps:
      - "Write personalized cold email for Persona 1"
      - "Create variant for Persona 2"
      - "Include CI/CD pain point in messaging"
    questions:
      - "Should I mention pricing in first email?"
    files:
      - "research_report.md"
    notes: "Focus on technical benefits, not features"
  reason: "Research complete, ready for outreach"
```

### Handoff Workflow

1. **Initiate** - Agent A completes partial work, creates handoff request
2. **Notify** - Agent B receives handoff request with full context
3. **Review** - Agent B processes context, asks clarifying questions if needed
4. **Accept** - Agent B accepts and continues work
5. **Continue** - Agent B can complete or handoff again

---

## 🎮 Using Handoffs in Dashboard

### Method 1: Manual Handoff

1. Go to **"Handoffs 🔄"** tab
2. Click **"Create Handoff"** sub-tab
3. Select "From Agent" (who's handing off)
4. Select "To Agent" (who's receiving)
5. Fill in:
   - Original Task
   - Work Completed
   - Key Findings
   - Next Steps
   - Reason
6. Click **"🔄 Initiate Handoff"**

### Method 2: Agent-Initiated (Coming Soon)

Agents will automatically request handoffs when they:
- Complete their portion of a task
- Encounter work outside their expertise
- Need another agent's skills to continue

---

## 📊 Monitoring Activity

### Activity Feed

Terminal-style view showing all events:

```
[10:23:45] [agent_online] 🟢 hunter: Agent Hunter came online
[10:24:12] [mission_created] 📋 orchestrator: Mission created: Q2 Campaign
[10:24:15] [task_started] 🔵 hunter: Task started: Write cold email sequence...
[10:25:30] [agent_message] 💬 scout → hunter: Here's the research you requested
[10:26:01] [handoff_request] 🔄 hunter → pepper: Handoff request: Email automation setup
[10:26:15] [handoff_accept] ✅ pepper: Handoff accepted by Pepper
[10:26:20] [task_completed] ✅ hunter: Task completed: ✓ Email sequence written
```

### Agent Chat View

See conversations between specific agents:

```
💬 Hunter ↔ Pepper

[Hunter] Here's the email sequence draft. Need your help setting up automation.
[Pepper] Got it. What's the trigger? Time-based or behavior-based?
[Hunter] Time-based: Day 0, 3, 7, 14
[Pepper] Perfect. I'll set up the workflow.
```

### Mission Activity Log

See everything that happened in a mission:

```
Mission: Q2 Campaign

[10:24:12] Created by user
[10:24:15] Task assigned to Scout
[10:25:01] Scout started research
[10:28:45] Scout completed research
[10:28:50] Handoff: Scout → Hunter
[10:29:00] Hunter accepted handoff
[10:29:15] Hunter started writing emails
...
```

---

## 🔍 Activity Summary

The system tracks:

- **Total Events** - Count of all activities
- **Event Types** - Breakdown by category
- **Active Agents** - How many agents have activity
- **Top Agents** - Most active agents
- **Conversations** - Active agent-to-agent chats
- **Missions Tracked** - Number of missions with activity

Access via **"Activity Feed 🔥"** → **Activity Summary** panel

---

## 💡 Example Workflows with Handoffs

### Sales Campaign

```
User: "Launch cold outreach campaign"

1. Scout researches 50 target companies
   → Hands off to Hunter with research findings

2. Hunter writes personalized cold emails
   → Hands off to Pepper for automation setup

3. Pepper sets up email sequences & tracking
   → Hands off to Sage for analytics dashboard

4. Sage monitors results, reports metrics
   → Mission complete
```

### Product Launch

```
User: "Launch new feature"

1. Shuri creates product requirements & roadmap
   → Hands off to Code for implementation

2. Code develops the feature
   → Hands off to Guardian for testing

3. Guardian runs QA, finds issues
   → Hands off back to Code for fixes

4. Code fixes issues
   → Hands off to Wong for documentation

5. Wong writes docs & release notes
   → Hands off to Quill for social announcement

6. Quill creates launch content
   → Mission complete
```

### Research Report

```
User: "Analyze competitors"

1. Scout researches 5 competitors
   → Hands off to Sage for data analysis

2. Sage analyzes market positioning
   → Hands off to Shuri for strategic recommendations

3. Shuri creates actionable recommendations
   → Hands off to Wong for executive summary

4. Wong writes final report
   → Mission complete
```

---

## 🛠️ Technical Details

### Architecture

```
┌─────────────────────────────────────────┐
│         Activity Tracker                │
│  - Logs all events                      │
│  - Maintains conversation threads       │
│  - Tracks agent activity                │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┼──────────────────────┐
│                  ▼                      │
│    ┌─────────────────────┐              │
│    │   Handoff Manager   │              │
│    │  - Creates handoffs │              │
│    │  - Routes requests  │              │
│    │  - Tracks status    │              │
│    └──────────┬──────────┘              │
│               │                         │
│    ┌──────────▼──────────┐              │
│    │    Message Bus      │              │
│    │  - Routes messages  │              │
│    │  - Broadcasts       │              │
│    └─────────────────────┘              │
└─────────────────────────────────────────┘
```

### Data Flow

1. **Event Occurs** → Agent completes task, sends message, etc.
2. **Message Published** → Sent to Message Bus
3. **Activity Tracker** → Logs event to history
4. **Dashboard** → Reads from Activity Tracker for display

### Persistence

- **Activity Log** - In-memory (last 1000 events)
- **Mission Logs** - Saved to `missions/{mission_id}_activity.json`
- **Agent Memory** - Each agent saves to `agents/{name}/memory/`

---

## 🚀 Next Enhancements

- [ ] **Auto-Handoff** - Agents automatically request handoffs
- [ ] **Handoff Suggestions** - AI suggests when to handoff
- [ ] **Group Chats** - Multiple agents in one conversation
- [ ] **Broadcast** - Message all agents at once
- [ ] **Activity Alerts** - Notify on specific events
- [ ] **Time-based Analytics** - Activity over time charts
