# Workspace v1.9.5 - Manager Auto-Start & Message Formatting Fix

## Summary
Fixed two issues:
1. **Manager now auto-starts** on dashboard load (unless safe mode is enabled)
2. **Message formatting fixed** - HTML is now properly escaped and rendered

## Changes Made

### 1. Manager Auto-Start (`dashboard.py`)

Added automatic Manager spawning on first dashboard load:

```python
# Auto-start Manager on first load (unless in safe mode)
if not st.session_state.manager_auto_started:
    data = get_data()
    if data:
        manager_running = any(a['name'] == 'Manager' for a in data['agents'])
        if not manager_running:
            safe_mode = os.environ.get('WORKSPACE_SAFE_MODE', '').lower() == 'true'
            if not safe_mode:
                # Spawn Manager automatically
                result = st.session_state.orchestrator.spawn_agent('manager')
                # Add welcome message
```

**Safe Mode:**
- Added checkbox in sidebar: "🔒 Safe Mode"
- When enabled, Manager won't auto-start on reload
- Useful for debugging or when you want manual control

### 2. Message Formatting Fix (`dashboard.py`)

Fixed HTML escaping in chat messages:

```python
def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )
```

Now:
- User messages are properly escaped (no raw HTML shown)
- Agent messages are escaped but tool result badges render correctly
- Newlines are converted to `<br>` tags
- Special characters don't break the HTML structure

## Before vs After

### Before (Formatting Issue)
```
User sees: "I'll spawn Code. <div style='background: #28a745...'>"
          (raw HTML code displayed instead of styled badge)
```

### After (Fixed)
```
User sees: "I'll spawn Code. ✓ spawn_agent" 
          (green badge rendered properly)
```

### Before (Manual Manager Spawn)
```
User opens dashboard → Empty agent list → Must click "Spawn Manager"
```

### After (Auto-Start)
```
User opens dashboard → Manager auto-starts → Welcome message appears
```

## How to Use Safe Mode

1. Check the "🔒 Safe Mode" checkbox in the sidebar
2. Reload the page
3. Manager will NOT auto-start
4. You can manually spawn agents as needed

## Files Changed

- `dashboard.py` - Added auto-start logic, safe mode toggle, HTML escaping

## Version
v1.9.5 - Manager Auto-Start & Formatting Fix
