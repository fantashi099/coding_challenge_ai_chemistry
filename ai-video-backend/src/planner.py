import time
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from .curated import curated_plan
from .models import VideoPlan

SYSTEM_PROMPT = """Create an accurate 4–7 scene high-school chemistry explainer.

SCRIPT
- Open with the core question, teach one idea per scene, and end with a recap.
- Write natural spoken narration totaling 140–360 words.
- Keep visual_text short and diagram-friendly. Never copy narration onto the screen.
- Use concept headings such as "Reading the scale"; never write "Scene 2" or similar labels.

VISUAL PLAN — these rules are mandatory
- Choose each scene's visual_kind from that scene's own content alone. Never copy the kind another scene used.
- Scene 1: title. Final scene: recap.
- Use at least 3 distinct visual kinds, and never use one kind more than twice.
- ph_scale: a pH number line, an acidity/basicity range, or real samples positioned on the scale.
- covalent_sharing: only electron-pair sharing or covalent bonds. A scene about ions, pH, or general rules is never covalent_sharing.
- ionic_transfer: only electron transfer and charged ions.
- bond_comparison: only side-by-side ionic/covalent contrasts.
- bullets: short rules, formulas, or explanations, including a logarithmic tenfold-change rule.
- Example plan for "How does the pH scale work?": title, ph_scale, bullets, ph_scale, recap.
- Every scene must advance a different visual idea. Do not repeat one animation with new text.
- Before answering, count your kinds and fix the plan if any kind appears more than twice.

STYLE
Design for Manim as a cinematic technical explainer: pure black canvas, sparse white type,
cyan/green neon accents, thin glowing outlines, animated nodes and paths, progressive reveals,
and generous empty space. Do not request photos, logos, branding, or unsupported effects."""


@dataclass(frozen=True)
class PlannerAttempt:
    attempt: int
    outcome: str
    elapsed_seconds: float
    http_status: int | None = None
    detail: str | None = None
    usage: dict[str, int | float] | None = None
    cost_usd: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlanningError(RuntimeError):
    def __init__(self, message: str, attempts: tuple[PlannerAttempt, ...] = ()):
        super().__init__(message)
        self.attempts = attempts


@dataclass(frozen=True)
class PlanningResult:
    plan: VideoPlan
    model: str
    usage: dict[str, Any]
    cost: float | None
    fallback_used: bool
    attempts: tuple[PlannerAttempt, ...] = ()


def _usage(payload: Any) -> dict[str, int | float]:
    source = payload.get("usage", {}) if isinstance(payload, dict) else {}
    allowed = ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
    return {key: source[key] for key in allowed if isinstance(source.get(key), (int, float))}


def _failure(
    attempt: int,
    started: float,
    exc: Exception,
    payload: Any,
    response: httpx.Response | None,
) -> PlannerAttempt:
    status = response.status_code if response else None
    if isinstance(exc, httpx.TimeoutException):
        outcome, detail = "timeout", "OpenRouter request timed out"
    elif isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        outcome, detail = "http_error", f"OpenRouter returned HTTP {status}"
    elif isinstance(exc, ValidationError):
        errors = exc.errors(include_url=False, include_context=False, include_input=False)
        detail = "; ".join(
            f"{'.'.join(map(str, error['loc'])) or 'plan'}: {error['msg']}" for error in errors
        )
        outcome = "validation_failed"
    elif isinstance(exc, (KeyError, TypeError, ValueError)):
        outcome, detail = "invalid_response", "OpenRouter response lacked valid structured content"
    else:
        outcome, detail = "network_error", type(exc).__name__
    usage = _usage(payload)
    return PlannerAttempt(
        attempt,
        outcome,
        round(time.monotonic() - started, 3),
        status,
        detail[:1000],
        usage or None,
        usage.get("cost"),
    )


def _retry_delay(response: httpx.Response | None) -> float:
    try:
        return min(max(float(response.headers.get("retry-after", 1)), 0), 30) if response else 1
    except ValueError:
        return 1


class OpenRouterPlanner:
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, timeout: float = 300):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def create(self, question: str) -> PlanningResult:
        attempts: list[PlannerAttempt] = []
        if self.api_key:
            messages: list[dict[str, str]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            plan_failures = 0
            for attempt in range(1, 4):
                started, payload, response = time.monotonic(), None, None
                try:
                    response = self.client.post(
                        self.endpoint,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "temperature": 0.2,
                            "max_tokens": 2500,
                            "reasoning": {"max_tokens": 1000},
                            "provider": {"require_parameters": True},
                            "messages": messages,
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
                    content = payload["choices"][0]["message"]["content"]
                    plan = (
                        VideoPlan.model_validate_json(content)
                        if isinstance(content, (str, bytes, bytearray))
                        else VideoPlan.model_validate(content)
                    )
                    usage = _usage(payload)
                    attempts.append(
                        PlannerAttempt(
                            attempt,
                            "succeeded",
                            round(time.monotonic() - started, 3),
                            response.status_code,
                            usage=usage or None,
                            cost_usd=usage.get("cost"),
                        )
                    )
                    return PlanningResult(
                        plan, self.model, usage, usage.get("cost"), False, tuple(attempts)
                    )
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
                    failure = _failure(attempt, started, exc, payload, response)
                    attempts.append(failure)
                    if failure.http_status in {429, 502, 503, 504} and attempt < 3:
                        time.sleep(_retry_delay(response))
                        continue
                    plan_failures += 1
                    if plan_failures >= 2 or attempt == 3:
                        break
                    if failure.outcome in {"validation_failed", "invalid_response"}:
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Your previous plan was rejected: {failure.detail}. Fix every violation and return a complete corrected plan.",
                            }
                        )

        fallback = curated_plan(question)
        if fallback:
            return PlanningResult(fallback, self.model, {}, None, True, tuple(attempts))
        reason = "OPENROUTER_API_KEY is not configured" if not self.api_key else f"{len(attempts)} attempts failed"
        raise PlanningError(f"Could not create a valid plan: {reason}", tuple(attempts))
