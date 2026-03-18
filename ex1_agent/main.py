"""
3 demo scenarios for Exercise 1:
  1. Standard refund — happy path with customer verification
  2. Large refund — hook intercepts and escalates
  3. Missing customer — gate blocks lookup_order
"""
from shared.utils import console
from ex1_agent.agent import AgentSession


def run_scenario(title: str, user_message: str) -> None:
    console.rule(f"[bold blue]{title}")
    session = AgentSession()
    messages = [{"role": "user", "content": user_message}]
    result = session.run(messages)
    console.print(f"\n[bold green]Final Response:[/]\n{result}\n")


if __name__ == "__main__":
    run_scenario(
        "Scenario 1: Standard Refund",
        "Hi, I'm john@example.com. I'd like a refund for order ORD-001 for $49.99."
    )
    run_scenario(
        "Scenario 2: Large Refund → Hook Intercepts",
        "I'm john@example.com and I need a full refund of $599 for order ORD-003."
    )
    run_scenario(
        "Scenario 3: Gate Blocks lookup_order (no customer verified)",
        "Please check the status of order ORD-001."
    )
