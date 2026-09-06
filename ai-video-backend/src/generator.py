import json
import time
from pathlib import Path
from typing import Protocol

from .config import Settings
from .media import ElevenLabsNarrator, FfmpegComposer, ManimRenderer, PiperNarrator, wav_duration
from .planner import OpenRouterPlanner, PlanningResult


class Planner(Protocol):
    def create(self, question: str) -> PlanningResult: ...


class Narrator(Protocol):
    def narrate(self, text: str, destination: Path) -> None: ...


class VideoGenerator:
    def __init__(
        self,
        settings: Settings | None = None,
        planner: Planner | None = None,
        narrator: Narrator | None = None,
        renderer: ManimRenderer | None = None,
        composer: FfmpegComposer | None = None,
    ):
        self.settings = settings or Settings()
        self.planner = planner or OpenRouterPlanner(
            self.settings.openrouter_api_key,
            self.settings.openrouter_model,
            timeout=self.settings.planner_timeout_seconds,
        )
        self.narrator = narrator or (
            ElevenLabsNarrator(
                self.settings.elevenlabs_api_key,
                self.settings.elevenlabs_voice_id,
                self.settings.elevenlabs_model,
            )
            if self.settings.elevenlabs_api_key
            else PiperNarrator(self.settings.piper_model, self.settings.piper_data_dir)
        )
        self.renderer = renderer or ManimRenderer()
        self.composer = composer or FfmpegComposer()

    def generate(self, question: str, output: Path) -> Path:
        started = time.monotonic()
        output.mkdir(parents=True, exist_ok=True)
        planning = self.planner.create(question)
        (output / "plan.json").write_text(
            json.dumps(planning.plan.model_dump(mode="json"), indent=2) + "\n"
        )

        visuals: list[Path] = []
        audio: list[Path] = []
        for index, scene in enumerate(planning.plan.scenes, 1):
            visual_path = output / "visuals" / f"scene-{index:02}.mp4"
            audio_path = output / "audio" / f"scene-{index:02}.wav"
            self.narrator.narrate(scene.narration, audio_path)
            self.renderer.render(scene, visual_path, index, len(planning.plan.scenes), wav_duration(audio_path))
            visuals.append(visual_path)
            audio.append(audio_path)

        video = output / "video.mp4"
        duration = self.composer.compose(visuals, audio, video)
        metadata = {
            "question": question,
            "model": planning.model,
            "token_usage": planning.usage,
            "reported_llm_cost_usd": planning.cost,
            "fallback_used": planning.fallback_used,
            "duration_seconds": round(duration, 3),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        return video
