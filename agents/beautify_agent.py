from __future__ import annotations

from pathlib import Path

from agents.base import Agent, PipelineContext
from beautify import beautify_video


class BeautifyAgent(Agent):
    name = "beautify"
    role = "ретушёр — сглаживает кожу и добавляет лёгкий макияж на лице (самый тяжёлый этап)"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        source = ctx.artifacts.get("montage") or ctx.output_dir / f"{ctx.project_dir.name}.mp4"
        source = Path(source)
        if not source.exists():
            ctx.warnings.append(
                f"[{self.name}] пропущено: нет исходного видео {source} "
                "(сначала должен отработать этап montage)"
            )
            return ctx
        out_path = ctx.output_dir / "beautified" / source.name
        beautify_video(source, out_path)
        ctx.artifacts["beautified"] = out_path
        return ctx
