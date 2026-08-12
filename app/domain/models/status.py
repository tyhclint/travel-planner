from typing import Literal

TaskName = Literal["flight", "accommodation", "web_search", "itinerary", "ranking"]
TaskStatus = Literal["not_required", "pending", "running", "completed", "stale", "failed"]
