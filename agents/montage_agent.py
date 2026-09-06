from __future__ import annotations

from agents.base import Agent, PipelineContext
from montage import render_project


class MontageAgent(Agent):
    name = "montage"
    role = "монтажёр — склеивает клипы, хук, аватар, подписи и музыку в один ролик"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        render_project(ctx.project_dir, ctx.output_dir, ctx.config)
        output_path = ctx.output_dir / f"{ctx.project_dir.name}.mp4"
        ctx.artifacts["montage"] = output_path
        return ctx
