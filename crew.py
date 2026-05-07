import os
from typing import List, Optional

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from tools.search_tool import create_search_tool
from tools.blackboard import BlackboardTool
from tools.slide_generator import SlideGeneratorTool


@CrewBase
class SpatioTemporalCrew:
    """Crew for spatio-temporal analogy analysis."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    _search_tool = None
    _blackboard = None
    _slide_tool = None

    def _get_search_tool(self):
        if self._search_tool is None:
            self._search_tool = create_search_tool()
        return self._search_tool

    def _get_blackboard(self):
        if self._blackboard is None:
            self._blackboard = BlackboardTool()
        return self._blackboard

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
        return Agent(
            config=self.agents_config["vertical_discovery"],
            verbose=True,
            allow_delegation=False,
            tools=[self._get_search_tool(), self._get_blackboard()],
        )

    @agent
    def horizontal_discovery(self) -> Agent:
        return Agent(
            config=self.agents_config["horizontal_discovery"],
            verbose=True,
            allow_delegation=False,
            tools=[self._get_search_tool(), self._get_blackboard()],
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
        return Task(config=self.tasks_config["abstraction_task"])

    @task
    def vertical_discovery_task(self) -> Task:
        return Task(config=self.tasks_config["vertical_discovery_task"])

    @task
    def horizontal_discovery_task(self) -> Task:
        return Task(config=self.tasks_config["horizontal_discovery_task"])

    @task
    def comparison_task(self) -> Task:
        return Task(config=self.tasks_config["comparison_task"])

    @task
    def causal_review_task(self) -> Task:
        return Task(config=self.tasks_config["causal_review_task"])

    @task
    def synthesis_task(self) -> Task:
        return Task(config=self.tasks_config["synthesis_task"])

    @task
    def visualization_task(self) -> Task:
        return Task(config=self.tasks_config["visualization_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
