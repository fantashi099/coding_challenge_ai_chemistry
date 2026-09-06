import json

import httpx
import pytest
from pydantic import ValidationError

from src.curated import CURATED_PLANS
from src.models import VideoPlan
from src.planner import OpenRouterPlanner, PlanningError


def test_schema_rejects_too_few_scenes_and_short_narration():
    with pytest.raises(ValidationError):
        VideoPlan.model_validate(
            {
                "title": "Too short",
                "scenes": [
                    {"heading": "One", "visual_text": "Text", "narration": "few words", "visual_kind": "title"}
                ],
            }
        )


def test_schema_rejects_repeated_visual_template():
    plan = next(iter(CURATED_PLANS.values())).model_dump()
    for scene in plan["scenes"]:
        scene["visual_kind"] = "covalent_sharing"
    with pytest.raises(ValidationError, match="first scene must be title"):
        VideoPlan.model_validate(plan)


def test_curated_plans_are_valid():
    assert len(CURATED_PLANS) == 3
    assert all(4 <= len(plan.scenes) <= 7 for plan in CURATED_PLANS.values())


def test_planner_retries_then_uses_curated_fallback():
    calls = 0

    def invalid_response(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    planner = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(invalid_response))
    )
    result = planner.create("How does the pH scale work?")
    assert calls == 2
    assert result.fallback_used is True


def test_planner_rejects_unknown_question_after_retry():
    def failure(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    planner = OpenRouterPlanner("key", "test-model", httpx.Client(transport=httpx.MockTransport(failure)))
    with pytest.raises(PlanningError, match="after 2 attempts"):
        planner.create("Explain an unknown chemistry topic")


def test_planner_accepts_structured_response():
    plan = next(iter(CURATED_PLANS.values()))

    def success(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        prompt = body["messages"][0]["content"]
        assert "cyan/green neon accents" in prompt
        assert "never use one kind more than twice" in prompt
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": plan.model_dump_json()}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.001},
            },
        )

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(success))
    ).create("question")
    assert result.plan == plan
    assert result.cost == 0.001
    assert result.fallback_used is False
