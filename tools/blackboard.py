from typing import Type, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class BlackboardInput(BaseModel):
    action: str = Field(
        ...,
        description="Either 'read' to get all entries, or 'write' to add a new anchor point"
    )
    content: str = Field(
        default="",
        description="The anchor point content to write (only used when action='write')"
    )


class BlackboardTool(BaseTool):
    name: str = "analysis_blackboard"
    description: str = (
        "Shared analysis blackboard for cross-pollination between horizontal and "
        "vertical discovery agents. Use 'write' to record key anchor points you "
        "discovered. Use 'read' to see what the other analyst has found."
    )
    args_schema: Type[BaseModel] = BlackboardInput

    _entries: List[str] = []

    def _run(self, action: str, content: str = "") -> str:
        if action == "write":
            if not content.strip():
                return "Error: empty content. Please provide an anchor point."
            self._entries.append(content)
            return f"Anchor point written to blackboard. Total entries: {len(self._entries)}"
        elif action == "read":
            if not self._entries:
                return "Blackboard is empty. No entries from other analysts yet."
            numbered = [f"[{i+1}] {e}" for i, e in enumerate(self._entries)]
            return "Blackboard entries:\n" + "\n".join(numbered)
        else:
            return f"Unknown action '{action}'. Use 'read' or 'write'."
