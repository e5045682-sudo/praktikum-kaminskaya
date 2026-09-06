from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineContext:
    """Общее состояние, которое агенты передают друг другу по цепочке."""

    project_dir: Path
    output_dir: Path
    config: dict
    artifacts: dict[str, Path | list[Path]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class Agent:
    """Базовый класс агента: у каждого своя роль и один метод run()."""

    name: str = "agent"
    role: str = ""

    def run(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError
