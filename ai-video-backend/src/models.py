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
        kinds = [scene.visual_kind for scene in self.scenes]
        if kinds[0] != VisualKind.TITLE or kinds[-1] != VisualKind.RECAP:
            raise ValueError("the first scene must be title and the final scene must be recap")
        if len(set(kinds)) < 3 or max(kinds.count(kind) for kind in set(kinds)) > 2:
            raise ValueError("use at least 3 visual kinds and no kind more than twice")
        return self
