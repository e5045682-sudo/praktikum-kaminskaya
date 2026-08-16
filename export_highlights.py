#!/usr/bin/env python3
"""Экспортирует каждый отрезок из "trim" в config.yaml проекта как отдельный
файл (для раздельной публикации, в отличие от montage.py, который склеивает
всё в один ролик). Быстро — без пересжатия видео.

Запуск:
    python export_highlights.py --project projects/interview
"""
import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Экспорт отрезков из config.yaml как отдельных файлов")
    parser.add_argument("--project", type=Path, required=True, help="Папка проекта (например projects/interview)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Куда сохранять (по умолчанию output/<имя_проекта>_highlights)")
    args = parser.parse_args()

    config_path = args.project / "config.yaml"
    if not config_path.exists():
        sys.exit(f"Не найден config.yaml: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    trims = config.get("trim", [])
    if not trims:
        sys.exit("В config.yaml нет секции 'trim' — нечего экспортировать")

    output_dir = args.output_dir or Path("output") / f"{args.project.name}_highlights"
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    for i, t in enumerate(trims, start=1):
        src = args.project / "clips" / t["file"]
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

    print(f"\nГотово! Файлы лежат в: {output_dir}")


if __name__ == "__main__":
    main()
