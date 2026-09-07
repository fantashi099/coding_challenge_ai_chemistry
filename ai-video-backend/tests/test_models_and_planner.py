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
    requests: list[httpx.Request] = []

    def invalid_response(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    planner = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(invalid_response))
    )
    result = planner.create("How does the pH scale work?")
    assert calls == 2
    assert result.fallback_used is True
    assert [attempt.outcome for attempt in result.attempts] == [
        "validation_failed", "validation_failed"
    ]
    assert all(attempt.http_status == 200 for attempt in result.attempts)
    assert all("input_value" not in (attempt.detail or "") for attempt in result.attempts)
    follow_up = json.loads(requests[1].content)["messages"][-1]
    assert follow_up["role"] == "user"
    assert "rejected" in follow_up["content"]


def test_planner_rejects_unknown_question_after_transient_retries(monkeypatch):
    monkeypatch.setattr("src.planner.time.sleep", lambda _: None)

    def failure(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="raw provider response must not be persisted")

    planner = OpenRouterPlanner("key", "test-model", httpx.Client(transport=httpx.MockTransport(failure)))
    with pytest.raises(PlanningError, match="3 attempts failed") as raised:
        planner.create("Explain an unknown chemistry topic")
    assert [attempt.http_status for attempt in raised.value.attempts] == [503, 503, 503]
    assert all(attempt.detail == "OpenRouter returned HTTP 503" for attempt in raised.value.attempts)


def test_planner_accepts_structured_response():
    plan = next(iter(CURATED_PLANS.values()))

    def success(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        assert "provider" not in body
        assert body["reasoning"] == {"max_tokens": 1000}
        assert body["max_tokens"] == 2500
        assert body["temperature"] == 0.0
        prompt = body["messages"][0]["content"]
        assert "cyan/green neon accents" in prompt
        assert "never use one kind more than twice" in prompt
        assert "first narration sentence" in prompt
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
    assert result.attempts[0].outcome == "succeeded"
    assert result.attempts[0].usage == {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.001}


def test_planner_accepts_structured_content_object():
    plan = next(iter(CURATED_PLANS.values()))

    def success(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": plan.model_dump()}}]})

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(success))
    ).create("question")
    assert result.plan == plan


def test_planner_repairs_deterministic_endpoint_visual_kinds():
    expected = next(iter(CURATED_PLANS.values()))
    returned = expected.model_dump()
    returned["scenes"][0]["visual_kind"] = "bullets"
    returned["scenes"][-1]["visual_kind"] = "bullets"

    def response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": returned}}]})

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(response))
    ).create("question")
    assert result.plan == expected
    assert len(result.attempts) == 1


@pytest.mark.parametrize(
    "question",
    [
        "How does the pH scale work?",
        "Why do atoms form covalent bonds?",
        "What is the difference between ionic and covalent bonding?",
    ],
)
def test_required_questions_are_grounded_with_exact_question_and_curated_baseline(question):
    baseline = CURATED_PLANS[question.casefold()]
    returned = baseline.model_dump()
    returned["scenes"][0]["narration"] = f"{question} {returned['scenes'][0]['narration']}"

    def response(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        user_prompt = body["messages"][1]["content"]
        assert f"sentence:\n{question}" in user_prompt
        assert baseline.model_dump_json(indent=2) in user_prompt
        return httpx.Response(
            200, json={"choices": [{"message": {"content": returned}}]}
        )

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(response))
    ).create(question)
    assert result.fallback_used is False


def test_planner_retries_a_paraphrased_opening_question():
    question = "How does the pH scale work?"
    plan = CURATED_PLANS[question.casefold()].model_dump()
    corrected = CURATED_PLANS[question.casefold()].model_dump()
    corrected["scenes"][0]["narration"] = f"{question} {corrected['scenes'][0]['narration']}"
    replies = [plan, corrected]
    requests = []

    def response(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": replies.pop(0)}}]})

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(response))
    ).create(question)
    assert len(result.attempts) == 2
    assert result.attempts[0].detail == f'first narration must begin exactly with: "{question}"'
    assert question in requests[1]["messages"][-1]["content"]


def test_transient_error_does_not_consume_validation_retry(monkeypatch):
    plan = next(iter(CURATED_PLANS.values()))
    replies = [
        httpx.Response(200, json={"choices": [{"message": {"content": {}}}]}),
        httpx.Response(429, headers={"retry-after": "0"}),
        httpx.Response(200, json={"choices": [{"message": {"content": plan.model_dump()}}]}),
    ]
    delays = []
    monkeypatch.setattr("src.planner.time.sleep", delays.append)

    def respond(request: httpx.Request) -> httpx.Response:
        return replies.pop(0)

    result = OpenRouterPlanner(
        "key", "test-model", httpx.Client(transport=httpx.MockTransport(respond))
    ).create("question")
    assert [attempt.outcome for attempt in result.attempts] == [
        "validation_failed", "http_error", "succeeded"
    ]
    assert delays == [0]
