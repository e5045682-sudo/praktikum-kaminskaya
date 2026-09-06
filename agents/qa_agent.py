from __future__ import annotations

from pathlib import Path

from agents.base import Agent, PipelineContext

MIN_SIZE_BYTES = 10_000


class QAAgent(Agent):
    name = "qa"
    role = "проверяющий — убеждается, что готовые файлы существуют и не пустые"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        checked = 0
        for key, value in ctx.artifacts.items():
            paths = value if isinstance(value, list) else [value]
            for raw_path in paths:
                checked += 1
                p = Path(raw_path)
                if not p.exists():
                    ctx.warnings.append(f"[{self.name}] {key}: файл не найден — {p}")
                elif p.stat().st_size < MIN_SIZE_BYTES:
                    size = p.stat().st_size
                    ctx.warnings.append(
                        f"[{self.name}] {key}: подозрительно маленький файл ({size} байт) — {p}"
                    )
        if checked == 0:
            ctx.warnings.append(f"[{self.name}] нечего проверять — ни один этап не создал файлов")
        return ctx
