import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .jobs import _now, question_key
from .models import VideoPlan
from .planner import OpenRouterPlanner, PlanningError, PlanningResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LearnedPlan:
    plan: VideoPlan
    source_model: str


class LearnedFallbackStore:
    def __init__(self, path: Path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS fallback_plans (
                    question_key TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    source_model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0
                )"""
            )

    def save(self, question: str, plan: VideoPlan, source_model: str) -> None:
        now = _now()
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO fallback_plans
                   (question_key, question, plan_json, source_model, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(question_key) DO UPDATE SET
                     question = excluded.question,
                     plan_json = excluded.plan_json,
                     source_model = excluded.source_model,
                     updated_at = excluded.updated_at""",
                (question_key(question), question, plan.model_dump_json(), source_model, now, now),
            )

    def use(self, question: str) -> LearnedPlan | None:
        key = question_key(question)
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT plan_json, source_model FROM fallback_plans WHERE question_key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            try:
                plan = VideoPlan.model_validate_json(row[0])
            except ValidationError as exc:
                logger.warning("ignoring invalid learned fallback for %r: %s", question, exc)
                return None
            db.execute(
                "UPDATE fallback_plans SET last_used_at = ?, use_count = use_count + 1 WHERE question_key = ?",
                (_now(), key),
            )
        return LearnedPlan(plan, row[1])


class FallbackPlanner:
    def __init__(self, primary: OpenRouterPlanner, learned: LearnedFallbackStore):
        self.primary = primary
        self.learned = learned
        self.last_source = "none"

    def create(self, question: str) -> PlanningResult:
        self.last_source = "none"
        try:
            result = self.primary.create(question)
        except PlanningError:
            cached = self.learned.use(question)
            if not cached:
                raise
            self.last_source = "learned"
            return PlanningResult(cached.plan, cached.source_model, {}, None, True)

        if not result.fallback_used:
            return result
        cached = self.learned.use(question)
        if cached:
            self.last_source = "learned"
            return PlanningResult(cached.plan, cached.source_model, {}, None, True)
        self.last_source = "curated"
        return result
