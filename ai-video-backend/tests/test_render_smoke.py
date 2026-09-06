import json
import shutil
import subprocess

import pytest

from src.curated import curated_plan
from src.generator import VideoGenerator
from src.media import ToneNarrator
from src.planner import PlanningResult


class CuratedPlanner:
    def create(self, question):
        return PlanningResult(curated_plan(question), "curated-test", {}, 0.0, True)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
def test_offline_render_produces_playable_audio_video(tmp_path):
    video = VideoGenerator(planner=CuratedPlanner(), narrator=ToneNarrator(0.5)).generate(
        "How does the pH scale work?", tmp_path / "render"
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(probe.stdout)
    assert {stream["codec_type"] for stream in data["streams"]} == {"video", "audio"}
    assert float(data["format"]["duration"]) > 1
