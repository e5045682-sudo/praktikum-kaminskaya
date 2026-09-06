#!/usr/bin/env python3
"""Экспортирует каждый отрезок из "trim" в config.yaml проекта как отдельный
файл (для раздельной публикации, в отличие от montage.py, который склеивает
всё в один ролик). Быстро — без пересжатия видео.

Запуск:
    python export_highlights.py --project projects/interview
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import yaml


def export_highlights(project_dir: Path, output_dir: Path | None = None) -> list[Path]:
    """Экспортирует каждый отрезок из trim в config.yaml проекта отдельным файлом.

    Вынесено из main() в переиспользуемую функцию — ей пользуется и CLI
    ниже, и HighlightsAgent из orchestrator.py.
    """
    config_path = project_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Не найден config.yaml: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    trims = config.get("trim", [])
    if not trims:
        raise ValueError("В config.yaml нет секции 'trim' — нечего экспортировать")

    output_dir = output_dir or Path("output") / f"{project_dir.name}_highlights"
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    exported: list[Path] = []

    for i, t in enumerate(trims, start=1):
        src = project_dir / "clips" / t["file"]
        if not src.exists():
            print(f"Пропускаю: не найден файл {src}")
            continue
        label = t.get("label", f"clip_{i:02d}")
        out_path = output_dir / f"{label}.mp4"
        duration = t["end"] - t["start"]
        cmd = [
            ffmpeg, "-y",
            "-ss", str(t["start"]),
            "-i", str(src),
            "-t", str(duration),
            "-c", "copy",
            str(out_path),
        ]
        print(f"[{i}/{len(trims)}] {label} ({t['start']}-{t['end']} сек)...")
        subprocess.run(cmd, check=True)
        exported.append(out_path)

    print(f"\nГотово! Файлы лежат в: {output_dir}")
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Экспорт отрезков из config.yaml как отдельных файлов")
    parser.add_argument("--project", type=Path, required=True, help="Папка проекта (например projects/interview)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Куда сохранять (по умолчанию output/<имя_проекта>_highlights)")
    args = parser.parse_args()

    try:
        export_highlights(args.project, args.output_dir)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
