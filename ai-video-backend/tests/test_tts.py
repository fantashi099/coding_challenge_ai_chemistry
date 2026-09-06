import json

import httpx

from src.config import Settings
from src.generator import VideoGenerator
from src.media import ElevenLabsNarrator, PiperNarrator


def test_generator_selects_elevenlabs_only_when_configured():
    assert isinstance(VideoGenerator(settings=Settings(_env_file=None)).narrator, PiperNarrator)
    settings = Settings(_env_file=None, elevenlabs_api_key="test-key")
    assert isinstance(VideoGenerator(settings=settings).narrator, ElevenLabsNarrator)


def test_elevenlabs_requests_configured_voice_and_converts_mp3(monkeypatch, tmp_path):
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"mp3", request=request)

    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))

    monkeypatch.setattr("src.media.shutil.which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr("src.media.subprocess.run", run)
    narrator = ElevenLabsNarrator(
        "test-key",
        "test-voice",
        "test-model",
        httpx.Client(transport=httpx.MockTransport(respond)),
    )
    destination = tmp_path / "audio" / "scene.wav"
    narrator.narrate("Chemistry narration", destination)

    request = requests[0]
    assert request.url.path.endswith("/test-voice")
    assert request.url.params["output_format"] == "mp3_44100_128"
    assert request.headers["xi-api-key"] == "test-key"
    assert json.loads(request.content) == {"text": "Chemistry narration", "model_id": "test-model"}
    assert commands[0][1]["input"] == b"mp3"
    assert commands[0][0][-1] == str(destination)
