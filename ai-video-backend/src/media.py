import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from manim import (
    BLUE_D, Circle, Create, Dot, DOWN, FadeIn, GREEN_D, GrowFromCenter,
    LaggedStart, LEFT, Line, ManimColor, ORIGIN, RIGHT, RoundedRectangle,
    Scene as ManimScene, Text, Transform, UP, VGroup, WHITE, Write, YELLOW,
    tempconfig,
)

from .models import Scene, VisualKind

BG, INK, MUTED, CYAN, GREEN, GOLD = "#000000", "#F4F7F8", "#89969C", "#00E5F0", "#00F57A", "#F6CF65"


def _fit(item, max_width: float):
    if item.width > max_width:
        item.scale_to_fit_width(max_width)
    return item


def _lines(text: str, width: int = 42) -> list[str]:
    result: list[str] = []
    for paragraph in text.splitlines():
        words, current = paragraph.strip().lstrip("•- ").split(), ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= width:
                current = candidate
            else:
                if current:
                    result.append(current)
                current = word
        if current:
            result.append(current)
    return result


class AnimatedSlide(ManimScene):
    spec: Scene
    scene_duration: float
    position: tuple[int, int]

    def construct(self) -> None:
        Text.set_default(font="DejaVu Sans")
        self.camera.background_color = ManimColor(BG)
        ambient = VGroup(
            Circle(radius=5.7, color=CYAN, stroke_width=2, stroke_opacity=0.05).shift(LEFT * 5.8 + DOWN * 3.8),
            Circle(radius=4.8, color=GREEN, stroke_width=2, stroke_opacity=0.04).shift(RIGHT * 6.2 + UP * 4.0),
        )
        page_box = RoundedRectangle(width=0.52, height=0.42, corner_radius=0.06, color="#17272B", fill_color="#061013", fill_opacity=1)
        page = Text(str(self.position[0]), font_size=13, color=MUTED).move_to(page_box)
        page_mark = VGroup(page_box, page).to_edge(DOWN, buff=0.3).to_edge(RIGHT, buff=0.35)
        target_duration = self.scene_duration + 1 / 30
        intro_duration = min(1.0, target_duration * 0.12)
        reveal_duration = min(6.0, target_duration * 0.45)
        self.add(ambient)
        if self.spec.visual_kind == VisualKind.TITLE:
            self.play(FadeIn(page_mark), run_time=intro_duration)
        else:
            heading = _fit(Text(self.spec.heading.upper(), font_size=24, weight="BOLD", color=INK), 8.6).to_edge(UP, buff=0.55)
            heading_box = RoundedRectangle(width=heading.width + 0.48, height=heading.height + 0.32, corner_radius=0.08, color="#18363B", stroke_width=1.5).move_to(heading)
            self.play(Create(heading_box), FadeIn(heading), FadeIn(page_mark), run_time=intro_duration)
        _, animations = self._visual()
        self.play(LaggedStart(*animations, lag_ratio=0.14), run_time=reveal_duration)
        self.wait(max(0.01, target_duration - intro_duration - reveal_duration))

    def _visual(self):
        if self.spec.visual_kind == VisualKind.TITLE:
            return self._hero()
        if self.spec.visual_kind == VisualKind.PH_SCALE:
            return self._ph_scale()
        if self.spec.visual_kind == VisualKind.COVALENT:
            return self._covalent()
        if self.spec.visual_kind == VisualKind.IONIC:
            return self._ionic()
        if self.spec.visual_kind == VisualKind.COMPARISON:
            return self._comparison()
        return self._bullets()

    def _hero(self):
        title = _fit(Text(self.spec.heading, font_size=54, weight="BOLD", color=CYAN), 10.5).shift(UP * 0.55)
        glow = title.copy().set_stroke(CYAN, width=14, opacity=0.22).set_fill(CYAN, opacity=0.08)
        copy = VGroup(*[Text(line, font_size=23, color=MUTED) for line in _lines(self.spec.visual_text, 68)]).arrange(DOWN, buff=0.14).shift(DOWN * 0.75)
        accent = Line(LEFT * 1.1, RIGHT * 1.1, color=GREEN, stroke_width=3).next_to(copy, DOWN, buff=0.42)
        group = VGroup(glow, title, copy, accent)
        return group, [FadeIn(glow), Write(title), FadeIn(copy, shift=UP * 0.2), Create(accent)]

    def _bullets(self):
        rows = VGroup()
        for line in _lines(self.spec.visual_text):
            label = _fit(Text(line, font_size=28, color=INK), 9.6)
            box = RoundedRectangle(width=label.width + 0.8, height=label.height + 0.48, corner_radius=0.08, color="#17383D", stroke_width=1.3)
            rows.add(VGroup(box, label, Dot(box.get_left() + LEFT * 0.32, radius=0.07, color=GREEN)))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.34).move_to(ORIGIN + DOWN * 0.1)
        return rows, [FadeIn(row, shift=RIGHT * 0.35) for row in rows]

    def _ph_scale(self):
        colors = ["#E63946", "#EF6A3A", "#F49D37", "#F9C74F", "#90BE6D", "#43AA8B", "#2A9D8F", "#35B8C8", "#2994D1", "#3777C2", "#5262B8", "#674EA7", "#7A3E9D", "#923E91", "#A63D80"]
        cells = VGroup()
        for number, color in enumerate(colors):
            box = RoundedRectangle(width=0.78, height=0.9, corner_radius=0.06, stroke_width=2, color=color, fill_color=color, fill_opacity=0.22)
            cells.add(VGroup(box, Text(str(number), font_size=20, weight="BOLD", color=WHITE)))
        cells.arrange(RIGHT, buff=0.035).shift(UP * 0.55)
        labels = VGroup(
            Text("ACIDIC", font_size=22, weight="BOLD", color="#FF9B9B").move_to(LEFT * 4.6 + DOWN * 0.25),
            Text("NEUTRAL", font_size=22, weight="BOLD", color="#A9E59B").move_to(DOWN * 0.25),
            Text("BASIC", font_size=22, weight="BOLD", color="#B9A8FF").move_to(RIGHT * 4.8 + DOWN * 0.25),
        )
        caption = VGroup(*[Text(line, font_size=25, color=INK) for line in _lines(self.spec.visual_text, 70)]).arrange(DOWN, buff=0.18).shift(DOWN * 1.35)
        scale_reveal = LaggedStart(*(GrowFromCenter(cell) for cell in cells), lag_ratio=0.06)
        return VGroup(cells, labels, caption), [scale_reveal, FadeIn(labels), FadeIn(caption, shift=UP * 0.2)]

    @staticmethod
    def _atom(label: str, color: str, x: float):
        halo = Circle(radius=0.91, color=color, stroke_width=14, stroke_opacity=0.12).shift(RIGHT * x)
        circle = Circle(radius=0.83, color=color, stroke_width=3, fill_color=BG, fill_opacity=1).shift(RIGHT * x)
        text = _fit(Text(label, font_size=34, weight="BOLD", color=WHITE), 1.2).move_to(circle)
        return VGroup(halo, circle, text)

    def _caption(self):
        return VGroup(*[Text(line, font_size=24, color=INK) for line in _lines(self.spec.visual_text, 72)]).arrange(DOWN, buff=0.14).shift(DOWN * 1.65)

    def _covalent(self):
        left, right = self._atom("A", BLUE_D, -2.4), self._atom("B", "#7451A6", 2.4)
        source = VGroup(Dot(LEFT * 1.35 + UP * 0.18, color=GOLD), Dot(RIGHT * 1.35 + DOWN * 0.18, color=GOLD))
        shared = VGroup(Dot(LEFT * 0.18 + UP * 0.1, color=GOLD), Dot(RIGHT * 0.18 + DOWN * 0.1, color=GOLD))
        bond, caption = Line(LEFT * 1.45, RIGHT * 1.45, color=CYAN, stroke_width=5), self._caption()
        return VGroup(left, right, source, bond, caption), [GrowFromCenter(left), GrowFromCenter(right), FadeIn(source), Transform(source, shared), Create(bond), FadeIn(caption, shift=UP * 0.2)]

    def _ionic(self):
        sodium, chlorine = self._atom("Na⁺", BLUE_D, -2.7), self._atom("Cl⁻", GREEN_D, 2.7)
        electron, target = Dot(LEFT * 1.55, color=GOLD), Dot(RIGHT * 1.55, color=GOLD)
        arrow, caption = Line(LEFT * 1.45, RIGHT * 1.45, color=GOLD, stroke_width=4).add_tip(), self._caption()
        return VGroup(sodium, chlorine, electron, arrow, caption), [GrowFromCenter(sodium), GrowFromCenter(chlorine), FadeIn(electron), Create(arrow), Transform(electron, target), FadeIn(caption, shift=UP * 0.2)]

    def _comparison(self):
        parts, cards = self.spec.visual_text.splitlines(), VGroup()
        for title, color, body in (("IONIC", CYAN, parts[0] if parts else "Opposite ions attract"), ("COVALENT", GREEN, parts[1] if len(parts) > 1 else "Electrons are shared")):
            card = RoundedRectangle(width=5.7, height=3.3, corner_radius=0.22, color=color, stroke_width=2, fill_color=color, fill_opacity=0.06)
            heading = Text(title, font_size=30, weight="BOLD", color=WHITE).move_to(card.get_top() + DOWN * 0.5)
            copy = VGroup(*[Text(line, font_size=22, color=WHITE) for line in _lines(body, 28)]).arrange(DOWN, buff=0.15).move_to(card.get_center() + DOWN * 0.2)
            cards.add(VGroup(card, heading, copy))
        cards.arrange(RIGHT, buff=0.45).shift(DOWN * 0.15)
        return cards, [FadeIn(card, shift=UP * 0.35) for card in cards]


class ManimRenderer:
    def render(self, scene: Scene, destination: Path, index: int, total: int, duration: float) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        AnimatedSlide.spec, AnimatedSlide.scene_duration, AnimatedSlide.position = scene, duration, (index, total)
        with tempconfig({"pixel_width": 1280, "pixel_height": 720, "frame_rate": 30, "background_color": BG, "media_dir": str(destination.parent / ".manim"), "output_file": destination.stem, "disable_caching": True, "write_to_movie": True, "preview": False, "verbosity": "WARNING"}):
            rendered = AnimatedSlide()
            rendered.render()
            produced = Path(rendered.renderer.file_writer.movie_file_path)
            os.replace(produced, destination)


class PiperNarrator:
    def __init__(self, model: str, data_dir: Path):
        self.model, self.data_dir = model, data_dir

    def _model_path(self) -> Path:
        supplied = Path(self.model)
        if supplied.is_file():
            return supplied
        model_path = self.data_dir / f"{self.model}.onnx"
        if not model_path.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "piper.download_voices", "--data-dir", str(self.data_dir), self.model], check=True)
        return model_path

    def narrate(self, text: str, destination: Path) -> None:
        executable = shutil.which("piper")
        if not executable:
            raise RuntimeError("Piper CLI is unavailable; run `uv sync` first")
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([executable, "--model", str(self._model_path()), "--output_file", str(destination)], input=text, text=True, check=True)


class ToneNarrator:
    """Deterministic audio used only by the offline compositor smoke test."""
    def __init__(self, duration: float = 0.35):
        self.duration = duration

    def narrate(self, text: str, destination: Path) -> None:
        rate = 16_000
        destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination), "wb") as output:
            output.setparams((1, 2, rate, int(rate * self.duration), "NONE", "not compressed"))
            frames = bytearray()
            for i in range(int(rate * self.duration)):
                frames.extend(int(3000 * math.sin(2 * math.pi * 440 * i / rate)).to_bytes(2, "little", signed=True))
            output.writeframes(frames)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        return source.getnframes() / source.getframerate()


class FfmpegComposer:
    def compose(self, visuals: list[Path], audio: list[Path], destination: Path) -> float:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg is required")
        clips = destination.parent / "clips"
        clips.mkdir(exist_ok=True)
        clip_paths, total = [], 0.0
        for index, (visual, narration) in enumerate(zip(visuals, audio, strict=True), 1):
            total += wav_duration(narration)
            clip = clips / f"scene-{index:02}.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(visual), "-i", str(narration), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(clip)], check=True)
            clip_paths.append(clip)
        concat = destination.parent / "concat.txt"
        concat.write_text("".join(f"file '{path.resolve()}'\n" for path in clip_paths))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(destination)], check=True)
        return total
