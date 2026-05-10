from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools.search_tool import create_search_tool
from tools.blackboard_tool import create_blackboard_tools
from tools.shared_blackboard import reset_blackboard
from tools.slide_generator import SlideGeneratorTool


@CrewBase
class SpatioTemporalCrew:
    """Crew for multi-agent analogy analysis with parallel agent discussion."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    _search_tool = None
    _blackboard_tools = {}
    _slide_tool = None

    def _get_search_tool(self):
        if self._search_tool is None:
            self._search_tool = create_search_tool()
        return self._search_tool

    def _get_blackboard_tools(self, agent_name: str):
        """Get blackboard tools for a specific agent."""
        if agent_name not in self._blackboard_tools:
            self._blackboard_tools[agent_name] = create_blackboard_tools(agent_name)
        return self._blackboard_tools[agent_name]

    def _get_slide_tool(self):
        if self._slide_tool is None:
            self._slide_tool = SlideGeneratorTool()
        return self._slide_tool

    @agent
    def abstracter(self) -> Agent:
        return Agent(
            config=self.agents_config["abstracter"],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def vertical_discovery(self) -> Agent:
        tools = [self._get_search_tool()] + self._get_blackboard_tools("vertical_discovery")
        return Agent(
            config=self.agents_config["vertical_discovery"],
            verbose=True,
            allow_delegation=False,
            tools=tools,
        )

    @agent
    def horizontal_discovery(self) -> Agent:
        tools = [self._get_search_tool()] + self._get_blackboard_tools("horizontal_discovery")
        return Agent(
            config=self.agents_config["horizontal_discovery"],
            verbose=True,
            allow_delegation=False,
            tools=tools,
        )

    @agent
    def comparator(self) -> Agent:
        return Agent(
            config=self.agents_config["comparator"],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def causal_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["causal_reviewer"],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def synthesizer(self) -> Agent:
        return Agent(
            config=self.agents_config["synthesizer"],
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def visualization_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["visualization_agent"],
            verbose=True,
            allow_delegation=False,
            tools=[self._get_slide_tool()],
        )

    @task
    def abstraction_task(self) -> Task:
        return Task(
            config=self.tasks_config["abstraction_task"],
        )

    @task
    def vertical_discovery_task(self) -> Task:
        return Task(
            config=self.tasks_config["vertical_discovery_task"],
        )

    @task
    def horizontal_discovery_task(self) -> Task:
        return Task(
            config=self.tasks_config["horizontal_discovery_task"],
        )

    @task
    def comparison_task(self) -> Task:
        return Task(
            config=self.tasks_config["comparison_task"],
        )

    @task
    def causal_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["causal_review_task"],
        )

    @task
    def synthesis_task(self) -> Task:
        return Task(
            config=self.tasks_config["synthesis_task"],
        )

    @task
    def visualization_task(self) -> Task:
        return Task(config=self.tasks_config["visualization_task"])

    @crew
    def crew(self) -> Crew:
        """
        Create crew with parallel execution for discovery agents.

        Execution flow:
        1. Abstracter (sequential) - generates lenses
        2. Vertical + Horizontal (parallel) - both use blackboard to discuss
        3. Comparator (sequential) - uses both outputs
        4. Causal Reviewer (sequential)
        5. Synthesizer (sequential)
        """
        # Get all agents and tasks
        all_agents = self.agents
        all_tasks = self.tasks

        # Filter out visualization
        analysis_agents = [a for a in all_agents if "visualization" not in a.role.lower()]
        analysis_tasks = [t for t in all_tasks if t.name != "visualization_task"]

        # Organize for staged execution
        # Stage 1: Abstracter only
        # Stage 2: Vertical + Horizontal (parallel)
        # Stage 3+: Comparator, Causal Reviewer, Synthesizer (sequential)

        return Crew(
            agents=analysis_agents,
            tasks=analysis_tasks,
            process=Process.sequential,
            verbose=True,
        )
