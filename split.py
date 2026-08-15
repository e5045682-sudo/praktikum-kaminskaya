#!/usr/bin/env python3
"""Разрезает одно видео на равные части по длительности (например, по 3 минуты).

Работает быстро — видео не пересжимается заново, а просто нарезается
"как есть", поэтому подходит даже для слабых компьютеров.

Из-за такого способа границы частей могут отличаться от заданной
длительности на несколько секунд (это нормально) — точная нарезка
секунда-в-секунду потребовала бы полного пересжатия и была бы намного
медленнее.

Запуск:
    python split.py "projects/example/clips/видео.mp4" --minutes 3
"""
import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def split_video(input_path: Path, output_dir: Path, chunk_seconds: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    pattern = str(output_dir / f"{input_path.stem}_part%03d{input_path.suffix}")
    cmd = [
        ffmpeg, "-y", "-i", str(input_path),
        "-c", "copy", "-map", "0",
        "-f", "segment", "-segment_time", str(chunk_seconds),
        "-reset_timestamps", "1",
        pattern,
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Разрезать видео на равные части")
    parser.add_argument("input", type=Path, help="Путь к исходному видео")
    parser.add_argument("--minutes", type=float, default=3, help="Длительность каждой части в минутах (по умолчанию 3)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Куда сохранять части (по умолчанию рядом с исходником, в папку <имя>_parts)")
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"Файл не найден: {args.input}")

    output_dir = args.output_dir or args.input.parent / f"{args.input.stem}_parts"
    chunk_seconds = int(args.minutes * 60)

    print(f"Разрезаю {args.input.name} на части по {args.minutes} мин...")
    split_video(args.input, output_dir, chunk_seconds)
    print(f"Готово! Части лежат в: {output_dir}")


if __name__ == "__main__":
    main()
