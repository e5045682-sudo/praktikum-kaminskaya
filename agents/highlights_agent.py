from __future__ import annotations

from agents.base import Agent, PipelineContext
from export_highlights import export_highlights


class HighlightsAgent(Agent):
    name = "highlights"
    role = "нарезчик хайлайтов — экспортирует отрезки из trim в config.yaml отдельными файлами"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        config_path = ctx.project_dir / "config.yaml"
        if not config_path.exists():
            ctx.warnings.append(f"[{self.name}] пропущено: нет config.yaml в {ctx.project_dir}")
            return ctx
        try:
            paths = export_highlights(
                ctx.project_dir, ctx.output_dir / f"{ctx.project_dir.name}_highlights"
            )
        except (FileNotFoundError, ValueError) as e:
            ctx.warnings.append(f"[{self.name}] пропущено: {e}")
            return ctx
        ctx.artifacts["highlights"] = paths
        return ctx
