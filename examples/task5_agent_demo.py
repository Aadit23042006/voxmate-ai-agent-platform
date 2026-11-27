"""Run: python examples/task5_agent_demo.py"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.agents.task5_runtime import Task5Agent, Task5Store

agent = Task5Agent(Task5Store(path="task5_demo.db"))
print("VoxMate Task 5 demo. Try: calculate 12 * (4 + 3), remember name = Aadit, recall my memory")
while True:
    try:
        prompt = input("You> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAgent> Session ended.")
        break
    if prompt.lower() in {"exit", "quit"}:
        break
    if not prompt:
        continue
    try:
        result = agent.run("demo-user", "demo-session", prompt)
        print("Agent>", result["response"])
        if result["tool_result"] is not None:
            print("Tool result:", result["tool_result"])
        print("Agent state:", result["agent_state"])
    except Exception as exc:
        print("Agent safety/error:", str(exc))
