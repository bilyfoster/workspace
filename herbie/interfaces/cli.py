"""Command Line Interface for Herbie"""
import argparse
import sys
import logging
from typing import Optional
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from herbie.core.orchestrator import Herbie
from herbie.core.config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HerbieCLI:
    """Interactive CLI for Herbie"""
    
    def __init__(self):
        self.herbie: Optional[Herbie] = None
        self.current_mission = None
    
    def print_banner(self):
        """Print welcome banner"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🤖 HERBIE - AI Squad Leader                                ║
║   Local Agent Orchestration System                           ║
║                                                              ║
║   Type 'help' for commands or describe your mission          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def print_help(self):
        """Print help text"""
        print("""
Commands:
  squad              - Show active squad members
  recruit <agents>   - Recruit agents (e.g., 'recruit pepper quill shuri')
  mission <desc>     - Plan a new mission
  missions           - List all missions
  mission <id>       - Show mission details
  run <mission_id>   - Execute next pending task in mission
  chat <message>     - Talk to Herbie
  status             - Show Herbie status
  clear              - Clear conversation history
  quit/exit          - Exit Herbie

Quick actions:
  Just type your mission and Herbie will help you plan it!
        """)
    
    def cmd_squad(self):
        """Show squad status"""
        if not self.herbie:
            print("❌ Herbie not initialized")
            return
        
        status = self.herbie.get_squad_status()
        
        if status['active_agents'] == 0:
            print("\n📭 Squad is empty. Use 'recruit <agent>' to add members.")
            print("Available agents: pepper, quill, shuri, wong, code")
            return
        
        print(f"\n🎯 Active Squad ({status['active_agents']} members):")
        print("-" * 60)
        
        for member in status['members']:
            avatar = member.get('avatar', '🤖')
            name = member['name']
            role = member['role']
            status_val = member['status']
            tasks = member.get('tasks_completed', 0)
            current = member.get('current_task', 'idle')
            
            status_icon = "🟢" if status_val == "idle" else "🔵" if status_val == "working" else "🔴"
            
            print(f"{avatar} {name} - {role}")
            print(f"   Status: {status_icon} {status_val} | Tasks: {tasks} | Current: {current}")
            print()
    
    def cmd_recruit(self, args):
        """Recruit agents to squad"""
        if not args:
            print("Usage: recruit <agent1> <agent2> ...")
            print("Available: pepper, quill, shuri, wong, code")
            return
        
        recruited = self.herbie.recruit_squad(args)
        
        if recruited:
            print(f"✅ Recruited: {', '.join(recruited)}")
        else:
            print("❌ Failed to recruit any agents")
    
    def cmd_mission(self, args):
        """Create or show mission"""
        if not args:
            # List missions
            missions = self.herbie.mission_manager.list_missions()
            if not missions:
                print("\n📭 No missions yet. Create one with: mission <description>")
                return
            
            print("\n📋 Missions:")
            print("-" * 60)
            for m in missions:
                status_icon = "🟢" if m.status.value == "active" else "✅" if m.status.value == "completed" else "⏸️"
                print(f"{status_icon} [{m.id}] {m.title}")
                print(f"   Status: {m.status.value} | Tasks: {len(m.tasks)}")
                print()
            return
        
        # Check if arg is a mission ID
        mission = self.herbie.mission_manager.get_mission(args[0])
        if mission:
            # Show mission details
            summary = self.herbie.get_mission_report(mission.id)
            if summary:
                print(f"\n📋 Mission: {summary['title']}")
                print(f"ID: {summary['mission_id']}")
                print(f"Status: {summary['status']}")
                print(f"Progress: {summary['progress']['percent']}% ({summary['progress']['completed']}/{summary['progress']['total']})")
                print("\nTasks:")
                for task in summary['tasks']:
                    icon = "✅" if task['status'] == 'completed' else "🔵" if task['status'] == 'in_progress' else "⏳"
                    assigned = f" @{task['assigned_to']}" if task['assigned_to'] else ""
                    print(f"  {icon} [{task['id']}] {task['description']}{assigned}")
            return
        
        # Create new mission plan
        goal = " ".join(args)
        print(f"\n🎯 Planning mission: {goal}")
        print("-" * 60)
        
        plan = self.herbie.plan_mission(goal)
        print(plan['plan'])
        
        print("\n💡 Tip: Recruit agents with 'recruit <names>' then create the mission.")
    
    def cmd_run(self, args):
        """Execute a task in a mission"""
        if not args:
            print("Usage: run <mission_id>")
            return
        
        mission_id = args[0]
        mission = self.herbie.mission_manager.get_mission(mission_id)
        
        if not mission:
            print(f"❌ Mission {mission_id} not found")
            return
        
        # Find next pending task
        pending = [t for t in mission.tasks if t.status == "pending"]
        if not pending:
            print("✅ All tasks completed!")
            return
        
        task = pending[0]
        print(f"\n🔹 Executing task: {task.description}")
        
        result = self.herbie.execute_task(
            mission_id=mission_id,
            task_id=task.id
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\n✅ Completed by {result['agent']}")
            print(f"\nResult:\n{result['result']}")
    
    def cmd_chat(self, args):
        """Chat with Herbie"""
        message = " ".join(args)
        print(f"\n🤖 Herbie:\n")
        response = self.herbie.chat(message)
        print(response)
    
    def cmd_status(self):
        """Show system status"""
        print("\n📊 Herbie Status:")
        print("-" * 60)
        print(f"Ollama: {'🟢 Connected' if self.herbie.ollama.is_healthy() else '🔴 Disconnected'}")
        print(f"Host: {config.ollama_host}")
        print(f"Default Model: {config.default_model}")
        print(f"Squad Size: {len(self.herbie.squad)} agents")
        print(f"Active Missions: {len(self.herbie.mission_manager.list_missions())}")
    
    def run(self):
        """Main CLI loop"""
        self.print_banner()
        
        # Initialize Herbie
        print("🚀 Initializing Herbie...")
        try:
            self.herbie = Herbie()
            
            if not self.herbie.ollama.is_healthy():
                print(f"\n⚠️  Warning: Cannot connect to Ollama at {config.ollama_host}")
                print("Make sure Ollama is running.")
            else:
                print("✅ Herbie is ready!")
                print("\n💡 Quick start: Type 'recruit pepper' to add your first agent")
                
        except Exception as e:
            print(f"❌ Failed to initialize Herbie: {e}")
            return
        
        # Main loop
        while True:
            try:
                user_input = input("\nherbie> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if cmd in ('quit', 'exit', 'q'):
                    print("👋 Goodbye!")
                    break
                
                elif cmd == 'help':
                    self.print_help()
                
                elif cmd == 'squad':
                    self.cmd_squad()
                
                elif cmd == 'recruit':
                    self.cmd_recruit(args)
                
                elif cmd == 'mission':
                    self.cmd_mission(args)
                
                elif cmd == 'missions':
                    self.cmd_mission([])
                
                elif cmd == 'run':
                    self.cmd_run(args)
                
                elif cmd == 'chat':
                    self.cmd_chat(args)
                
                elif cmd == 'status':
                    self.cmd_status()
                
                elif cmd == 'clear':
                    self.herbie.messages = [self.herbie.messages[0]] if self.herbie.messages else []
                    print("🧹 Conversation history cleared")
                
                else:
                    # Treat as chat/mission
                    print(f"\n🎯 Processing: {user_input}")
                    plan = self.herbie.plan_mission(user_input)
                    print(plan['plan'])
                    print("\n💡 Use 'recruit <agent>' to build your squad, then 'run <mission_id>' to execute.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.exception("Error in CLI")
                print(f"❌ Error: {e}")

def main():
    """Entry point"""
    cli = HerbieCLI()
    cli.run()

if __name__ == "__main__":
    main()
