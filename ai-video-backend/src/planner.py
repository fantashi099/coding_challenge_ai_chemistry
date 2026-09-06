from dataclasses import dataclass
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

    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, timeout: float = 60):
        self.api_key = api_key
        self.model = model
        self.client = client or httpx.Client(timeout=timeout)

    def create(self, question: str) -> PlanningResult:
        last_error: Exception = PlanningError("OPENROUTER_API_KEY is not configured")
        if self.api_key:
            messages: list[dict[str, str]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            for _ in range(2):
                try:
                    response = self.client.post(
                        self.endpoint,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": self.model,
                            "temperature": 0.2,
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
                    plan = VideoPlan.model_validate_json(payload["choices"][0]["message"]["content"])
                    usage = payload.get("usage", {})
                    return PlanningResult(plan, self.model, usage, usage.get("cost"), False)
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
                    last_error = exc
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Your previous plan was rejected: {exc}. Fix every violation and return a complete corrected plan.",
                        }
                    )

        fallback = curated_plan(question)
        if fallback:
            return PlanningResult(fallback, self.model, {}, None, True)
        raise PlanningError(f"Could not create a valid plan after 2 attempts: {last_error}") from last_error
