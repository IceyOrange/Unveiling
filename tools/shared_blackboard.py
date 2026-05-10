"""
Thread-safe shared blackboard for multi-agent discussion.
Allows parallel agents to write and read in real-time.
"""
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional


class SharedBlackboard:
    """Thread-safe singleton blackboard for agent discussion."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._messages = []
                    cls._instance._agents_done = set()
                    cls._instance._created_at = datetime.now().isoformat()
        return cls._instance

    def write(self, agent: str, content: str, stage: str = "") -> str:
        """
        Thread-safe write to blackboard.

        Args:
            agent: Agent name (e.g., "vertical_discovery")
            content: Message content
            stage: Current stage (e.g., "discovery", "comparison")

        Returns:
            Confirmation message
        """
        with self._lock:
            message = {
                "agent": agent,
                "content": content,
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
            }
            self._messages.append(message)
            count = len(self._messages)
            return f"[{agent}] 已写入讨论板 (当前 {count} 条消息)"

    def read(self, last_n: int = 10, agent_filter: Optional[str] = None) -> List[Dict]:
        """
        Read recent messages from blackboard.

        Args:
            last_n: Number of recent messages to return
            agent_filter: Optional agent name to filter by

        Returns:
            List of message dictionaries
        """
        with self._lock:
            messages = self._messages[-last_n:] if last_n > 0 else self._messages.copy()
            if agent_filter:
                messages = [m for m in messages if m["agent"] == agent_filter]
            return messages

    def read_all(self) -> List[Dict]:
        """Read all messages."""
        with self._lock:
            return self._messages.copy()

    def mark_done(self, agent: str) -> str:
        """Mark an agent as done."""
        with self._lock:
            self._agents_done.add(agent)
            return f"[{agent}] 已标记完成"

    def is_done(self, agent: str) -> bool:
        """Check if an agent is done."""
        with self._lock:
            return agent in self._agents_done

    def wait_for_agents(self, agents: List[str], timeout: int = 300) -> bool:
        """
        Wait for specified agents to mark themselves as done.

        Args:
            agents: List of agent names to wait for
            timeout: Maximum wait time in seconds

        Returns:
            True if all agents done, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if all(a in self._agents_done for a in agents):
                    return True
            time.sleep(0.5)
        return False

    def get_summary(self) -> str:
        """Get formatted summary of all messages."""
        with self._lock:
            if not self._messages:
                return "讨论板为空"
            summary = []
            for msg in self._messages:
                preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                summary.append(f"[{msg['agent']}]: {preview}")
            return "\n\n".join(summary)

    def clear(self):
        """Clear all messages (for new analysis)."""
        with self._lock:
            self._messages.clear()
            self._agents_done.clear()

    def get_stats(self) -> Dict:
        """Get blackboard statistics."""
        with self._lock:
            return {
                "total_messages": len(self._messages),
                "agents_done": list(self._agents_done),
                "created_at": self._created_at,
            }


# Global singleton instance
blackboard = SharedBlackboard()


def get_blackboard() -> SharedBlackboard:
    """Get the global blackboard instance."""
    return blackboard


def reset_blackboard():
    """Reset blackboard for new analysis."""
    blackboard.clear()
