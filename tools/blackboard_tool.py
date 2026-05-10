"""
Enhanced Blackboard Tool for CrewAI agents.
Supports parallel writing, reading, and completion marking.
"""
from typing import Type, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from tools.shared_blackboard import get_blackboard


class BlackboardWriteInput(BaseModel):
    """Input for writing to blackboard."""
    content: str = Field(
        ...,
        description="The message content to write to the blackboard"
    )
    stage: str = Field(
        default="",
        description="Current stage (e.g., 'discovery', 'comparison')"
    )


class BlackboardReadInput(BaseModel):
    """Input for reading from blackboard."""
    last_n: int = Field(
        default=10,
        description="Number of recent messages to read (0 for all)"
    )
    agent_filter: str = Field(
        default="",
        description="Optional agent name to filter by"
    )


class BlackboardDoneInput(BaseModel):
    """Input for marking agent as done."""
    empty: str = Field(
        default="",
        description="Empty parameter (no input needed)"
    )


class EnhancedBlackboardTool(BaseTool):
    """
    Enhanced shared blackboard for cross-agent discussion.

    Supports:
    - write: Add a message to the blackboard
    - read: Read recent messages from other agents
    - done: Mark yourself as complete
    - summary: Get full discussion summary
    """

    name: str = "discussion_blackboard"
    description: str = """
    Shared discussion blackboard for real-time agent communication.

    Available commands:
    - write: Post your findings, questions, or responses to the discussion
    - read: See what other agents have recently written
    - done: Mark yourself as complete (triggers next stage)
    - summary: Get full discussion summary

    Example usage:
    - write(content="Found key pattern in 1980s data")
    - read(last_n=5)
    - done()
    - summary()

    Use this to:
    1. Share discoveries with other agents in real-time
    2. Respond to or question other agents' findings
    3. Coordinate analysis direction
    4. Avoid redundant work
    """
    args_schema: Type[BaseModel] = BlackboardWriteInput
    agent_name: str = "unknown"

    def __init__(self, agent_name: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.blackboard = get_blackboard()

    def _run(self, content: str, stage: str = "", command: str = "write") -> str:
        """Execute blackboard command."""
        if command == "write":
            return self.blackboard.write(self.agent_name, content, stage)
        elif command == "read":
            messages = self.blackboard.read(last_n=10)
            return self._format_messages(messages)
        elif command == "done":
            return self.blackboard.mark_done(self.agent_name)
        elif command == "summary":
            return self.blackboard.get_summary()
        else:
            return f"Unknown command: {command}. Use: write, read, done, or summary"

    def _format_messages(self, messages: List[dict]) -> str:
        """Format messages for display."""
        if not messages:
            return "讨论板暂无消息"

        formatted = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")[:19]  # Truncate milliseconds
            formatted.append(
                f"[{msg['agent']} at {timestamp}]:\n{msg['content']}"
            )
        return "\n\n---\n\n".join(formatted)


class BlackboardWriteTool(BaseTool):
    """Tool for writing to blackboard."""

    model_config = ConfigDict(extra="allow")

    name: str = "blackboard_write"
    description: str = """
    Write a message to the shared blackboard for other agents to see.

    Use this when you:
    - Discover important patterns or anchor points
    - Want to share findings with other agents
    - Have questions or suggestions for other agents
    - Find something that might influence their analysis

    Example: blackboard_write(content="Found key turning point in 1980s")
    """
    args_schema: Type[BaseModel] = BlackboardWriteInput

    def __init__(self, agent_name: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.blackboard = get_blackboard()

    def _run(self, content: str, stage: str = "") -> str:
        return self.blackboard.write(self.agent_name, content, stage)


class BlackboardReadTool(BaseTool):
    """Tool for reading from blackboard."""

    model_config = ConfigDict(extra="allow")

    name: str = "blackboard_read"
    description: str = """
    Read recent messages from the shared blackboard.

    Use this to:
    - See what other agents have discovered
    - Get context before starting your analysis
    - Check for responses to your earlier messages
    - Coordinate with other agents

    Parameters:
    - last_n: Number of recent messages to read (default: 10, use 0 for all)
    - agent_filter: Optional agent name to filter by

    Example: blackboard_read(last_n=5)
    """
    args_schema: Type[BaseModel] = BlackboardReadInput

    def __init__(self, agent_name: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.blackboard = get_blackboard()

    def _run(self, last_n: int = 10, agent_filter: str = "") -> str:
        messages = self.blackboard.read(last_n=last_n if last_n > 0 else 0, agent_filter=agent_filter or None)
        return self._format_messages(messages)

    def _format_messages(self, messages: List[dict]) -> str:
        if not messages:
            return "讨论板暂无消息"

        formatted = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")[:19]
            agent_stage = f" ({msg['stage']})" if msg.get("stage") else ""
            formatted.append(
                f"[{msg['agent']}{agent_stage} at {timestamp}]:\n{msg['content']}"
            )
        return "\n\n---\n\n".join(formatted)


class BlackboardDoneTool(BaseTool):
    """Tool for marking agent as done."""

    model_config = ConfigDict(extra="allow")

    name: str = "blackboard_done"
    description: str = """
    Mark yourself as done with your analysis.

    Call this when you have:
    - Completed all your assigned tasks
    - Written your key findings to the blackboard
    - Responded to other agents' messages (if needed)

    This signals the system that you're ready for the next stage.

    Example: blackboard_done()
    """
    args_schema: Type[BaseModel] = BlackboardDoneInput

    def __init__(self, agent_name: str = "unknown", **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.blackboard = get_blackboard()

    def _run(self, empty: str = "") -> str:
        return self.blackboard.mark_done(self.agent_name)


def create_blackboard_tools(agent_name: str):
    """
    Create a set of blackboard tools for an agent.

    Args:
        agent_name: Name of the agent (e.g., "vertical_discovery")

    Returns:
        List of blackboard tools
    """
    return [
        BlackboardWriteTool(agent_name=agent_name),
        BlackboardReadTool(agent_name=agent_name),
        BlackboardDoneTool(agent_name=agent_name),
    ]
