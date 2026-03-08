#!/usr/bin/env python3
"""
Diagnostic script for Workspace
Run this to check if agent spawning is working
"""
import sys
sys.path.insert(0, '.')

print("="*70)
print("WORKSPACE DIAGNOSTIC TOOL")
print("="*70)

# 1. Check imports
print("\n1. Checking imports...")
try:
    from workspace_orchestrator import get_orchestrator
    from shared.agent_tools import get_tool_registry
    print("   ✅ All imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# 2. Initialize orchestrator
print("\n2. Initializing orchestrator...")
try:
    orch = get_orchestrator()
    print(f"   ✅ Orchestrator ready (v{orch.version})")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# 3. Check available agents
print("\n3. Checking available agents...")
available = orch.list_available_agents()
print(f"   Found {len(available)} agent souls: {', '.join(available[:5])}...")

# 4. Check current state
print("\n4. Current system state:")
data = orch.get_dashboard_data()
print(f"   Active agents: {len(data['agents'])}")
for a in data['agents']:
    print(f"     - {a['name']} ({a['status']})")
print(f"   Active missions: {len([m for m in data['missions'] if m['status'] == 'active'])}")

# 5. Test tool registry
print("\n5. Testing tool registry...")
registry = get_tool_registry(orch)
print(f"   Registered tools: {len(registry.tools)}")
for name in list(registry.tools.keys())[:3]:
    print(f"     - {name}")

# 6. Test tool parsing
print("\n6. Testing tool call parsing...")
test_response = '''I'll help you! 

[tool:spawn_agent]{"name": "code"}

Let me know if you need anything else.'''

calls = registry.parse_tool_calls(test_response)
print(f"   Found {len(calls)} tool call(s)")
if calls:
    for call in calls:
        print(f"     - {call.tool_name}: {call.arguments}")

# 7. Test actual spawn (if not already running)
print("\n7. Testing agent spawn...")
if not any(a['name'] == 'Code' for a in data['agents']):
    import json
    result = registry.execute_tool("spawn_agent", name="code")
    result_data = json.loads(result)
    
    if result_data.get('success'):
        print(f"   ✅ Code agent spawned successfully!")
        print(f"      ID: {result_data['result'].get('agent_id')}")
    else:
        print(f"   ❌ Spawn failed: {result_data.get('error')}")
else:
    print("   ℹ️ Code agent already running")

# 8. Final status
print("\n8. Final agent status:")
data = orch.get_dashboard_data()
print(f"   Total agents: {len(data['agents'])}")
for a in data['agents']:
    print(f"     - {a['name']} ({a['status']})")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)

# Cleanup
print("\nCleaning up test agents...")
for aid in list(orch.agents.keys()):
    orch.kill_agent(aid)
    print(f"   Stopped {aid}")
