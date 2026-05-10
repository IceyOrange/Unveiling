"""
Brainstorm Room - Multi-round agent discussion.

Simulates a real brainstorming session where agents:
1. Start with independent research (Round 0)
2. Share findings on the blackboard
3. Respond to each other's discoveries in subsequent rounds
4. Request Abstracter to refine concepts when needed
5. Continue until convergence or max rounds
"""

import json
import re
from typing import List, Dict, Optional
from crewai import Task, Crew, Process
from tools.shared_blackboard import get_blackboard


class BrainstormRoom:
    """
    A brainstorming room where Vertical and Horizontal agents discuss
    in multiple rounds, like experts in a meeting room.
    """

    def __init__(self, vertical_agent, horizontal_agent, abstracter_agent, max_rounds=3):
        self.vertical = vertical_agent
        self.horizontal = horizontal_agent
        self.abstracter = abstracter_agent
        self.max_rounds = max_rounds
        self.blackboard = get_blackboard()
        self.round = 0
        self.topic = ""
        self.initial_lenses = []

    def run(self, topic: str, lenses: List[str]) -> Dict:
        """
        Run the brainstorming session.

        Returns:
            Dict with discussion_summary, final_lenses, converged
        """
        self.topic = topic
        self.initial_lenses = lenses

        # Round 0: Independent research
        self._run_round_0()

        # Rounds 1-N: Interactive discussion
        for round_num in range(1, self.max_rounds + 1):
            self.round = round_num
            converged = self._run_discussion_round()

            if converged:
                break

        # Final abstraction: extract refined lenses from discussion
        final_lenses = self._extract_final_lenses()

        return {
            "rounds": self.round,
            "converged": converged if round_num < self.max_rounds else False,
            "initial_lenses": self.initial_lenses,
            "final_lenses": final_lenses,
            "discussion_summary": self.blackboard.get_summary(),
            "messages": self.blackboard.read_all(),
        }

    def _run_round_0(self):
        """Round 0: Both agents do independent research."""
        print(f"\n{'='*60}")
        print(f"BRAINSTORM ROUND 0: Independent Research")
        print(f"{'='*60}")

        # Vertical independent search
        v_task = Task(
            description=f"""
主题：{self.topic}
初始抽象透镜：{', '.join(self.initial_lenses)}

你是 Vertical Discovery Agent（历史追溯专家）。
请基于以上透镜，独立搜索历史中的相关实例。
不要管其他人在做什么，专注于你自己的发现。

要求：
1. 每个透镜至少找到 1-2 个历史实例
2. 说明实例与透镜的关联
3. 如果有特别有趣的发现，使用 blackboard_write 工具写入讨论板

输出格式：
- 透镜1: [实例列表]
- 透镜2: [实例列表]
- 意外发现: [如果有]
""",
            agent=self.vertical,
            expected_output="历史实例列表",
        )
        v_result = self.vertical.execute_task(v_task)
        self.blackboard.write("vertical_discovery", str(v_result), "round_0_independent")

        # Horizontal independent search
        h_task = Task(
            description=f"""
主题：{self.topic}
初始抽象透镜：{', '.join(self.initial_lenses)}

你是 Horizontal Discovery Agent（跨领域类比专家）。
请基于以上透镜，独立搜索当前不同领域的相关实例。
不要管其他人在做什么，专注于你自己的发现。

要求：
1. 每个透镜至少找到 1-2 个跨领域实例
2. 说明实例与透镜的关联
3. 如果有特别有趣的发现，使用 blackboard_write 工具写入讨论板

输出格式：
- 透镜1: [实例列表]
- 透镜2: [实例列表]
- 意外发现: [如果有]
""",
            agent=self.horizontal,
            expected_output="跨领域实例列表",
        )
        h_result = self.horizontal.execute_task(h_task)
        self.blackboard.write("horizontal_discovery", str(h_result), "round_0_independent")

        print(f"Round 0 complete. Blackboard messages: {len(self.blackboard.read_all())}")

    def _run_discussion_round(self) -> bool:
        """
        Run one round of interactive discussion.
        Both agents see all previous messages and respond.

        Returns:
            True if converged, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"BRAINSTORM ROUND {self.round}: Interactive Discussion")
        print(f"{'='*60}")

        # Get all previous discussion
        history = self.blackboard.read_all()
        history_text = self._format_history(history)

        # Vertical responds
        v_task = Task(
            description=f"""
主题：{self.topic}
初始透镜：{', '.join(self.initial_lenses)}

=== 讨论历史 ===
{history_text}

=== 你的角色 ===
你是 Vertical Discovery Agent（历史追溯专家）。

请阅读以上讨论历史，然后：
1. 回应 Horizontal Discovery Agent 的观点（同意、补充、质疑均可）
2. 分享你基于对方观点想到的新发现
3. 如果对方提出了你没想到的角度，请深入挖掘
4. 如果你认为讨论已经足够深入，请明确说 "CONVERGED"
5. 如果你发现现有透镜不够用了，请说 "NEED_ABSTRACTION: 原因"

注意：
- 使用 blackboard_write 工具分享你的关键发现
- 保持具体，不要泛泛而谈
- 每个观点都要有历史实例支撑
""",
            agent=self.vertical,
            expected_output="你的回应和分析",
        )
        v_result = self.vertical.execute_task(v_task)
        v_text = str(v_result)
        self.blackboard.write("vertical_discovery", v_text, f"round_{self.round}")

        # Check if Vertical requested abstraction
        if "NEED_ABSTRACTION" in v_text.upper():
            self._summon_abstracter()

        # Horizontal responds (sees Vertical's new message too)
        h_task = Task(
            description=f"""
主题：{self.topic}
初始透镜：{', '.join(self.initial_lenses)}

=== 讨论历史 ===
{history_text}

=== Vertical Agent 刚刚说 ===
{v_text}

=== 你的角色 ===
你是 Horizontal Discovery Agent（跨领域类比专家）。

请阅读以上讨论（包括 Vertical 刚刚的发言），然后：
1. 回应 Vertical Discovery Agent 的观点
2. 基于对方的发现，搜索新的跨领域类比
3. 如果对方的历史发现可以映射到其他领域，请指出
4. 如果你认为讨论已经足够深入，请明确说 "CONVERGED"
5. 如果你发现现有透镜不够用了，请说 "NEED_ABSTRACTION: 原因"

注意：
- 使用 blackboard_write 工具分享你的关键发现
- 保持具体，每个类比都要有实例支撑
- 尝试在对方的历史模式中发现跨领域映射
""",
            agent=self.horizontal,
            expected_output="你的回应和分析",
        )
        h_result = self.horizontal.execute_task(h_task)
        h_text = str(h_result)
        self.blackboard.write("horizontal_discovery", h_text, f"round_{self.round}")

        # Check if Horizontal requested abstraction
        if "NEED_ABSTRACTION" in h_text.upper():
            self._summon_abstracter()

        # Check convergence
        converged = self._check_convergence(v_text, h_text)

        print(f"Round {self.round} complete. Converged: {converged}")
        print(f"Blackboard messages: {len(self.blackboard.read_all())}")

        return converged

    def _summon_abstracter(self):
        """Summon Abstracter to refine or create new lenses."""
        print(f"\n{'='*40}")
        print(f"ABSTRACTER SUMMONED")
        print(f"{'='*40}")

        history = self.blackboard.read_all()
        history_text = self._format_history(history)

        a_task = Task(
            description=f"""
主题：{self.topic}
当前透镜：{', '.join(self.initial_lenses)}

=== 讨论历史 ===
{history_text}

=== 你的角色 ===
你是 Abstracter（概念抽象专家）。

基于以上讨论，请你：
1. 提炼讨论中出现的新概念或新模式
2. 评估当前透镜是否需要修正、细化或新增
3. 如果有新透镜，给出：名称 + 定义 + 为什么有价值

输出格式：
现有透镜评估：
- 透镜1: [保留/修正/细化] + 理由
- 透镜2: ...

新提炼的透镜（如有）：
- 新透镜1: [名称] - [定义] - [价值]
""",
            agent=self.abstracter,
            expected_output="透镜评估和新透镜",
        )
        a_result = self.abstracter.execute_task(a_task)
        self.blackboard.write("abstracter", str(a_result), f"round_{self.round}_abstraction")

        print(f"Abstracter response recorded.")

    def _check_convergence(self, v_text: str, h_text: str) -> bool:
        """
        Check if discussion has converged.

        Convergence signals:
        1. Agent explicitly says CONVERGED
        2. Both responses are very short (no new info)
        3. Both responses repeat previous points
        """
        # Explicit convergence signal
        if "CONVERGED" in v_text.upper() and "CONVERGED" in h_text.upper():
            return True

        # Check for meaningful content
        v_has_content = len(v_text) > 200 and not v_text.startswith("Error")
        h_has_content = len(h_text) > 200 and not h_text.startswith("Error")

        if not v_has_content and not h_has_content:
            return True

        return False

    def _extract_final_lenses(self) -> List[str]:
        """Extract final refined lenses from discussion."""
        history = self.blackboard.read_all()
        history_text = self._format_history(history)

        a_task = Task(
            description=f"""
主题：{self.topic}
初始透镜：{', '.join(self.initial_lenses)}

=== 完整讨论历史 ===
{history_text}

=== 你的角色 ===
你是 Abstracter（概念抽象专家）。

基于以上完整讨论，请提炼最终的抽象透镜列表。
这些透镜应该：
1. 覆盖讨论中的所有重要发现
2. 比初始透镜更精确、更有洞察力
3. 能够用于后续的比较和因果分析

输出格式（JSON）：
{{
    "lenses": [
        {{
            "name": "透镜名称",
            "definition": "简短定义",
            "evidence": "支持这个透镜的关键证据"
        }}
    ]
}}
""",
            agent=self.abstracter,
            expected_output="JSON格式的透镜列表",
        )
        a_result = self.abstracter.execute_task(a_task)

        # Try to extract JSON
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*\}', str(a_result), re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return [l["name"] for l in data.get("lenses", [])]
        except Exception:
            pass

        # Fallback: return initial lenses
        return self.initial_lenses

    def _format_history(self, messages: List[Dict]) -> str:
        """Format discussion history for prompt."""
        if not messages:
            return "（讨论刚开始，还没有历史消息）"

        formatted = []
        for msg in messages:
            agent = msg.get("agent", "unknown")
            content = msg.get("content", "")
            stage = msg.get("stage", "")
            formatted.append(f"[{agent} | {stage}]:\n{content}\n")

        return "\n---\n".join(formatted)
