import argparse
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Settings
from src.models import VideoPlan
from src.planner import SYSTEM_PROMPT

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def main() -> None:
    parser = argparse.ArgumentParser(description="One planner-only request; no render, no retry, no fallback")
    parser.add_argument("--question", default="How does the pH scale work?")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    settings = Settings()
    api_key, model = settings.openrouter_api_key, settings.openrouter_model
    if not api_key:
        sys.exit("OPENROUTER_API_KEY is not set")

    started = time.monotonic()
    response = httpx.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=args.timeout,
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": args.question},
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
    message = response.json()["choices"][0]["message"]
    print(f"{model} answered in {time.monotonic() - started:.1f}s")
    try:
        plan = VideoPlan.model_validate_json(message["content"])
    except ValueError as exc:
        print(f"REJECTED: {exc}")
        sys.exit(1)
    kinds = [scene.visual_kind.value for scene in plan.scenes]
    print("VALID:", " | ".join(f"{kind} ({scene.heading})" for kind, scene in zip(kinds, plan.scenes)))
    print(f"kinds={len(set(kinds))} max_repeat={max(kinds.count(kind) for kind in set(kinds))}")


if __name__ == "__main__":
    main()
