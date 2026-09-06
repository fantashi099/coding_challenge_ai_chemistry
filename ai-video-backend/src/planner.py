from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from .curated import curated_plan
from .models import VideoPlan


class PlanningError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlanningResult:
    plan: VideoPlan
    model: str
    usage: dict[str, Any]
    cost: float | None
    fallback_used: bool


class OpenRouterPlanner:
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=60)

    def create(self, question: str) -> PlanningResult:
        last_error: Exception = PlanningError("OPENROUTER_API_KEY is not configured")
        if self.api_key:
            for _ in range(2):
                try:
                    response = self.client.post(
                        self.endpoint,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "temperature": 0.2,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Create an accurate, concise high-school chemistry video plan. Narration must total 140–360 words. Visual text must be brief and readable on a slide.",
                                },
                                {"role": "user", "content": question},
                            ],
                            "response_format": {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "chemistry_video_plan",
                                    "strict": True,
                                    "schema": VideoPlan.model_json_schema(),
                                },
                            },
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    plan = VideoPlan.model_validate_json(payload["choices"][0]["message"]["content"])
                    usage = payload.get("usage", {})
                    return PlanningResult(plan, self.model, usage, usage.get("cost"), False)
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
                    last_error = exc

        fallback = curated_plan(question)
        if fallback:
            return PlanningResult(fallback, self.model, {}, None, True)
        raise PlanningError(f"Could not create a valid plan after 2 attempts: {last_error}") from last_error
