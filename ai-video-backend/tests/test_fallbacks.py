import sqlite3

import pytest

from src.curated import CURATED_PLANS
from src.fallbacks import FallbackPlanner, LearnedFallbackStore
from src.planner import PlanningError, PlanningResult


class PrimaryPlanner:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def create(self, question):
        if self.error:
            raise self.error
        return self.result


def test_learned_fallback_is_used_after_primary_failure(tmp_path):
    repository = LearnedFallbackStore(tmp_path / "jobs.sqlite3")
    plan = next(iter(CURATED_PLANS.values()))
    repository.save("New topic", plan, "source-model")
    planner = FallbackPlanner(PrimaryPlanner(error=PlanningError("offline")), repository)

    result = planner.create(" new   TOPIC ")
    assert result.plan == plan
    assert result.model == "source-model"
    assert planner.last_source == "learned"
    with sqlite3.connect(repository.path) as db:
        assert db.execute("SELECT use_count FROM fallback_plans").fetchone()[0] == 1


def test_learned_fallback_precedes_curated_but_not_live_result(tmp_path):
    repository = LearnedFallbackStore(tmp_path / "jobs.sqlite3")
    plans = list(CURATED_PLANS.values())
    repository.save("required question", plans[0], "cached-model")

    curated = PlanningResult(plans[1], "live-model", {}, None, True)
    planner = FallbackPlanner(PrimaryPlanner(result=curated), repository)
    assert planner.create("required question").plan == plans[0]
    assert planner.last_source == "learned"

    live = PlanningResult(plans[1], "live-model", {}, 0.01, False)
    planner = FallbackPlanner(PrimaryPlanner(result=live), repository)
    assert planner.create("required question") == live
    assert planner.last_source == "none"


def test_curated_result_and_corrupt_cache_are_handled(tmp_path):
    repository = LearnedFallbackStore(tmp_path / "jobs.sqlite3")
    plan = next(iter(CURATED_PLANS.values()))
    with sqlite3.connect(repository.path) as db:
        db.execute(
            "INSERT INTO fallback_plans VALUES (?, ?, ?, ?, ?, ?, NULL, 0)",
            ("broken", "broken", "{}", "model", "now", "now"),
        )
    assert repository.use("broken") is None

    curated = PlanningResult(plan, "model", {}, None, True)
    planner = FallbackPlanner(PrimaryPlanner(result=curated), repository)
    assert planner.create("uncached") == curated
    assert planner.last_source == "curated"

    with pytest.raises(PlanningError):
        FallbackPlanner(PrimaryPlanner(error=PlanningError("offline")), repository).create("missing")
