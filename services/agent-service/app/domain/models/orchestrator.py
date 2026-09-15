from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


OrchestratorRoute = Literal[
    "flight_agent",
    "accommodation_agent",
    "destination_research_agent",
    "itinerary_planner_agent",
    "user_clarification",
    "response_agent",
]

OrchestratorRerunTask = Literal[
    "flight",
    "accommodation",
    "destination_research",
    "itinerary",
]

PARALLEL_ORCHESTRATOR_ROUTES: set[OrchestratorRoute] = {
    "flight_agent",
    "accommodation_agent",
    "destination_research_agent",
}


class OrchestratorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_tasks: list[OrchestratorRoute] = Field(min_length=1)
    can_answer_now: bool = False
    needs_clarification: bool = False
    clarification_fields: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    rerun_completed_tasks: list[OrchestratorRerunTask] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_route_consistency(self) -> Self:
        next_tasks = set(self.next_tasks)

        if "response_agent" in next_tasks and len(next_tasks) > 1:
            raise ValueError("response_agent cannot be combined with other next_tasks.")

        if "user_clarification" in next_tasks and len(next_tasks) > 1:
            raise ValueError("user_clarification cannot be combined with other next_tasks.")

        if len(next_tasks) > 1 and not next_tasks.issubset(PARALLEL_ORCHESTRATOR_ROUTES):
            raise ValueError("Only independent search/research agents can run in parallel.")

        if self.can_answer_now and self.next_tasks != ["response_agent"]:
            raise ValueError("can_answer_now requires next_tasks to be only response_agent.")

        if self.needs_clarification:
            if self.next_tasks != ["user_clarification"]:
                raise ValueError(
                    "needs_clarification requires next_tasks to be only user_clarification."
                )
            if not self.clarification_fields:
                raise ValueError("needs_clarification requires clarification_fields.")

        return self
