#!/usr/bin/env python3
"""Оркестратор: управляет командой агентов, которые вместе собирают ролик
из одного проекта.

Каждый агент (agents/*.py) отвечает за один этап и получает общий
PipelineContext — так следующий агент видит, что сделал предыдущий
(например beautify берёт файл, который построил montage). Если один
агент упал с ошибкой, оркестратор не прерывает весь проект — он
записывает предупреждение и передаёт управление дальше по цепочке,
а на следующий проект переходит в любом случае.

Доступные агенты:
    montage     — склеивает клипы, хук, аватар, подписи и музыку
    highlights  — экспортирует отрезки из trim отдельными файлами
    beautify    — сглаживание кожи (тяжёлая операция, выключена по умолчанию)
    qa          — проверяет, что готовые файлы существуют и не пустые

Порядок этапов по умолчанию — DEFAULT_PIPELINE ниже. Для конкретного
проекта его можно переопределить полем `pipeline` в
projects/<name>/config.yaml:

    pipeline: [montage, beautify, qa]

Запуск:
    python orchestrator.py --project projects/example
    python orchestrator.py --all
    python orchestrator.py --project projects/example --only montage,qa
    python orchestrator.py --project projects/example --skip beautify
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from agents.base import Agent, PipelineContext
from agents.beautify_agent import BeautifyAgent
from agents.highlights_agent import HighlightsAgent
from agents.montage_agent import MontageAgent
from agents.qa_agent import QAAgent
from montage import load_base_config, load_project_config

AGENTS: dict[str, type[Agent]] = {
    "montage": MontageAgent,
    "highlights": HighlightsAgent,
    "beautify": BeautifyAgent,
    "qa": QAAgent,
}

DEFAULT_PIPELINE = ["montage", "qa"]


def resolve_stage_names(
    project_config: dict, only: list[str] | None, skip: list[str] | None
) -> list[str]:
    stage_names = list(project_config.get("pipeline", DEFAULT_PIPELINE))
    if only:
        stage_names = [s for s in stage_names if s in only] or list(only)
    if skip:
        stage_names = [s for s in stage_names if s not in skip]
    return stage_names


def run_project(
    project_dir: Path,
    output_dir: Path,
    base_config: dict,
    only: list[str] | None,
    skip: list[str] | None,
) -> PipelineContext:
    project_config = load_project_config(project_dir, base_config)
    stage_names = resolve_stage_names(project_config, only, skip)

    print(f"\n{'=' * 60}")
    print(f"Проект: {project_dir.name}")
    print(f"Команда агентов: {' -> '.join(stage_names) if stage_names else '(пусто)'}")
    print("=" * 60)

    ctx = PipelineContext(project_dir=project_dir, output_dir=output_dir, config=base_config)
    for stage_name in stage_names:
        agent_cls = AGENTS.get(stage_name)
        if agent_cls is None:
            msg = f"неизвестный этап пайплайна: {stage_name}"
            print(f"! {msg}")
            ctx.warnings.append(msg)
            continue

        agent = agent_cls()
        print(f"\n--- [{agent.name}] {agent.role} ---")
        start = time.time()
        try:
            ctx = agent.run(ctx)
        except Exception as e:
            elapsed = time.time() - start
            print(f"ОШИБКА в этапе '{agent.name}' ({elapsed:.1f} сек): {e}")
            ctx.warnings.append(f"[{agent.name}] ошибка: {e}")
            continue
        elapsed = time.time() - start
        print(f"Готово за {elapsed:.1f} сек")

    return ctx


def print_summary(results: dict[str, PipelineContext]) -> None:
    print(f"\n{'=' * 60}")
    print("ИТОГ")
    print("=" * 60)
    for project_name, ctx in results.items():
        status = "OK" if not ctx.warnings else f"{len(ctx.warnings)} предупреждений"
        print(f"\n{project_name}: {status}")
        for key, value in ctx.artifacts.items():
            paths = value if isinstance(value, list) else [value]
            for p in paths:
                print(f"  [{key}] {p}")
        for w in ctx.warnings:
            print(f"  ! {w}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Оркестратор команды агентов монтажа")
    parser.add_argument("--project", type=Path, help="Путь к одному проекту")
    parser.add_argument(
        "--projects-dir", type=Path, default=Path("projects"), help="Папка со всеми проектами"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="Куда сохранять результаты"
    )
    parser.add_argument("--all", action="store_true", help="Обработать все проекты")
    parser.add_argument(
        "--only", type=str, default=None, help="Выполнить только эти этапы через запятую, например montage,qa"
    )
    parser.add_argument("--skip", type=str, default=None, help="Пропустить эти этапы через запятую")
    args = parser.parse_args()

    only = args.only.split(",") if args.only else None
    skip = args.skip.split(",") if args.skip else None

    base_config = load_base_config()

    if args.all:
        if not args.projects_dir.is_dir():
            sys.exit(f"Папка с проектами не найдена: {args.projects_dir}")
        project_dirs = sorted(p for p in args.projects_dir.iterdir() if p.is_dir())
        if not project_dirs:
            sys.exit(f"В папке {args.projects_dir} нет проектов")
    elif args.project:
        project_dirs = [args.project]
    else:
        parser.error("Укажите --project <папка> или --all")
        return

    results = {}
    for project_dir in project_dirs:
        ctx = run_project(project_dir, args.output_dir, base_config, only, skip)
        results[project_dir.name] = ctx

    print_summary(results)

    if any(ctx.warnings for ctx in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
