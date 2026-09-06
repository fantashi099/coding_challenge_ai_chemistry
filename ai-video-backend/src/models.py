from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class VisualKind(StrEnum):
    TITLE = "title"
    BULLETS = "bullets"
    PH_SCALE = "ph_scale"
    COVALENT = "covalent_sharing"
    IONIC = "ionic_transfer"
    COMPARISON = "bond_comparison"
    RECAP = "recap"


class Scene(BaseModel):
    heading: str = Field(min_length=1, max_length=80)
    visual_text: str = Field(min_length=1, max_length=300)
    narration: str = Field(min_length=1, max_length=1200)
    visual_kind: VisualKind


class VideoPlan(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    scenes: list[Scene] = Field(min_length=4, max_length=7)

    @model_validator(mode="after")
    def narration_length(self) -> "VideoPlan":
        words = sum(len(scene.narration.split()) for scene in self.scenes)
        if not 140 <= words <= 360:
            raise ValueError(f"total narration must be 140–360 words, got {words}")
        return self
