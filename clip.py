#!/usr/bin/env python3
"""Вырезает один произвольный отрезок из видео (без пересжатия, быстро).

Запуск:
    python clip.py "projects/interview/clips/видео.mp4" --start 926 --end 1046 --output sample.mp4

--start и --end — в секундах.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def main() -> None:
    parser = argparse.ArgumentParser(description="Вырезать один отрезок из видео")
    parser.add_argument("input", type=Path, help="Путь к исходному видео")
    parser.add_argument("--start", type=float, required=True, help="Начало отрезка, сек")
    parser.add_argument("--end", type=float, required=True, help="Конец отрезка, сек")
    parser.add_argument("--output", type=Path, default=Path("sample.mp4"), help="Куда сохранить результат")
    args = parser.parse_args()

    if not args.input.exists():
        sys.exit(f"Файл не найден: {args.input}")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    duration = args.end - args.start
    cmd = [
        ffmpeg, "-y",
        "-ss", str(args.start),
        "-i", str(args.input),
        "-t", str(duration),
        "-c", "copy",
        str(args.output),
    ]
    subprocess.run(cmd, check=True)
    print(f"Готово: {args.output}")


if __name__ == "__main__":
    main()
