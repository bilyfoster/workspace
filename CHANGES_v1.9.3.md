# Workspace v1.9.3 - Manager Tool System

## Summary
Implemented a tool system that allows the Manager agent to actually EXECUTE commands instead of just talking about them. This is inspired by the swarms framework where agents can call functions to take action.

## Files Changed

### NEW: shared/agent_tools.py
Tool registry and execution system:
- `ToolRegistry`: Parses tool calls from agent responses using regex patterns
- `ToolCall`: Dataclass representing parsed tool calls
- `AgentTool`: Wrapper for tool functions with metadata
- Tools available: spawn_agent, kill_agent, list_agents, get_status, create_mission

### MODIFIED: agents/manager/soul.md
Updated Manager with tool instructions:
- Tool usage format: `[tool:spawn_agent]{"name": "code"}`
- Instructions to ACTUALLY spawn agents when needed
- Tool command reference with examples
- Response format requiring tool calls for action

### MODIFIED: agent_runner.py
Added tool execution in `_chat()`:
- Parses tool calls from agent response after generation
- Executes each tool via tool_registry
- Appends results to response for user visibility

### MODIFIED: workspace_orchestrator.py
Updated `_build_manager_context()`:
- Includes tool descriptions in context sent to Manager
- Shows available agents that can be spawned

### MODIFIED: dashboard.py
Added message formatting:
- `format_message_with_tools()`: Separates main content from tool results
- `format_tool_results()`: Renders tool execution as styled badges

## Tool Usage Patterns Supported

1. **Bracket format**: `[tool:spawn_agent]{"name": "code"}`
2. **JSON block**:
   ```json
   {"tool": "list_agents"}
   ```
3. **TOOL_CALL format**: `TOOL_CALL: spawn_agent : {"name": "code"}`

## Flow Example

```
User: "I need help coding a Python function"

Manager receives:
  === WORKSPACE SYSTEM STATE ===
  ACTIVE AGENTS (1):
    🟢 Manager (idle)
  AVAILABLE TO SPAWN: code, pixel, shuri, ...
  
  ## Available Tools
  ### spawn_agent
  Creates a new agent by name.
  Usage: [tool:spawn_agent]{"name": "agent_name"}
  ...
  
Manager responds:
  "I'll spawn the Code specialist to help you with that.
   [tool:spawn_agent]{"name": "code"}"

_agent_runner._chat() parses the tool call:
  - Detects [tool:spawn_agent]{"name": "code"}
  - Calls tool_registry.execute_tool("spawn_agent", name="code")
  - Spawns the agent via orchestrator
  
Result appended to response:
  "\n\n[Tool Execution Results]\n✓ spawn_agent: {'spawned': True, 'agent_id': 'code-1234', ...}"

User sees formatted response with success badge.
```

## Testing

To test the new system:

1. Start the dashboard: `streamlit run dashboard.py`
2. Spawn Manager: Click "Manager" in sidebar, click Spawn
3. Chat with Manager: "I need help coding"
4. Manager should respond with `[tool:spawn_agent]{"name": "code"}` in the response
5. Code agent should appear in the HUD automatically

## Version
v1.9.3 - Manager Tool System
