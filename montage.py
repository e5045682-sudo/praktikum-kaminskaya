#!/usr/bin/env python3
"""Автоматический монтаж видеороликов: склейка клипов, переходы, хук, аватар,
подписи и фоновая музыка. Работает с одним проектом или пакетно по папке.

Структура проекта (папка projects/<name>/):
    clips/          — исходные клипы, склеиваются в порядке имён файлов
    hook.mp4         — (опц.) короткий ролик, приклеивается в начало
    avatar.mp4|.png  — (опц.) оверлей поверх видео в углу (picture-in-picture)
    music.mp3        — (опц.) фоновая музыка
    config.yaml      — (опц.) настройки проекта, см. config.example.yaml

Текстовые подписи (captions в config.yaml) требуют установленного ImageMagick
(https://imagemagick.org/script/download.php) — без него эту секцию из
config.yaml нужно убрать.

Запуск:
    python montage.py --project projects/example
    python montage.py --all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
import moviepy.video.fx.all as vfx

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}

DEFAULT_CONFIG = {
    "transition_duration": 0.5,
    "resolution": None,
    "fps": 30,
    "music_volume": 0.2,
    "avatar": {
        "position": "bottom-right",
        "width_ratio": 0.28,
        "margin": 24,
    },
}

CORNER_POSITIONS = {
    "top-left": lambda w, h, cw, ch, m: (m, m),
    "top-right": lambda w, h, cw, ch, m: (w - cw - m, m),
    "bottom-left": lambda w, h, cw, ch, m: (m, h - ch - m),
    "bottom-right": lambda w, h, cw, ch, m: (w - cw - m, h - ch - m),
}

DEFAULT_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_project_config(project_dir: Path, base_config: dict) -> dict:
    config = dict(base_config)
    config["avatar"] = dict(base_config["avatar"])
    config_path = project_dir / "config.yaml"
    if config_path.exists():
        user_config = load_yaml(config_path)
        avatar_override = user_config.pop("avatar", None)
        config.update(user_config)
        if avatar_override:
            config["avatar"].update(avatar_override)
    return config


def find_clips(project_dir: Path) -> list[Path]:
    clips_dir = project_dir / "clips"
    if not clips_dir.is_dir():
        raise FileNotFoundError(f"Не найдена папка с клипами: {clips_dir}")
    clips = sorted(p for p in clips_dir.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)
    if not clips:
        raise FileNotFoundError(f"В папке {clips_dir} нет видеофайлов")
    return clips


def find_optional_file(project_dir: Path, stem: str, extensions) -> Path | None:
    for ext in extensions:
        candidate = project_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def resolve_font(config: dict) -> str:
    font = config.get("font")
    if font:
        return font
    for candidate in DEFAULT_FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "Не найден системный шрифт для подписей. "
        "Укажите путь к .ttf файлу в config.yaml, ключ 'font'."
    )


def build_main_sequence(clip_paths: list[Path], config: dict) -> VideoFileClip:
    trims_by_file: dict[str, list[dict]] = {}
    for t in config.get("trim", []):
        trims_by_file.setdefault(t["file"], []).append(t)

    raw_clips = []
    for path in clip_paths:
        file_trims = trims_by_file.get(path.name)
        if file_trims:
            # несколько отрезков из одного файла — каждый становится
            # отдельным куском в итоговой склейке, в указанном порядке
            for t in file_trims:
                clip = VideoFileClip(str(path))
                start = t.get("start", 0)
                end = t.get("end", clip.duration)
                raw_clips.append(clip.subclip(start, end))
        else:
            raw_clips.append(VideoFileClip(str(path)))

    duration = config.get("transition_duration", 0)
    if not duration or len(raw_clips) == 1:
        return concatenate_videoclips(raw_clips, method="compose")

    positioned = [raw_clips[0]]
    t_cursor = raw_clips[0].duration
    for clip in raw_clips[1:]:
        start = max(0, t_cursor - duration)
        faded = clip.crossfadein(duration).set_start(start)
        positioned.append(faded)
        t_cursor = start + clip.duration
    return CompositeVideoClip(positioned).set_duration(t_cursor)


def add_hook(main_clip, project_dir: Path):
    hook_path = project_dir / "hook.mp4"
    if not hook_path.exists():
        return main_clip
    hook_clip = VideoFileClip(str(hook_path))
    if hook_clip.size != main_clip.size:
        hook_clip = hook_clip.resize(newsize=main_clip.size)
    return concatenate_videoclips([hook_clip, main_clip], method="compose")


def add_avatar(main_clip, project_dir: Path, config: dict):
    avatar_path = find_optional_file(project_dir, "avatar", (".mp4", ".mov", ".png", ".jpg", ".jpeg"))
    if avatar_path is None:
        return main_clip

    avatar_cfg = config["avatar"]
    w, h = main_clip.size

    if avatar_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        avatar_clip = ImageClip(str(avatar_path)).set_duration(main_clip.duration)
    else:
        avatar_clip = VideoFileClip(str(avatar_path))
        if avatar_clip.duration < main_clip.duration:
            avatar_clip = avatar_clip.fx(vfx.loop, duration=main_clip.duration)
        else:
            avatar_clip = avatar_clip.subclip(0, main_clip.duration)
        avatar_clip = avatar_clip.without_audio()

    target_width = int(w * avatar_cfg["width_ratio"])
    avatar_clip = avatar_clip.resize(width=target_width)
    x, y = CORNER_POSITIONS[avatar_cfg["position"]](w, h, avatar_clip.w, avatar_clip.h, avatar_cfg["margin"])
    avatar_clip = avatar_clip.set_position((x, y))

    return CompositeVideoClip([main_clip, avatar_clip], size=main_clip.size).set_duration(main_clip.duration)


def add_captions(main_clip, config: dict):
    captions = config.get("captions", [])
    if not captions:
        return main_clip

    font = resolve_font(config)
    layers = [main_clip]
    for cap in captions:
        text_clip = (
            TextClip(
                cap["text"],
                font=font,
                fontsize=cap.get("font_size", 60),
                color=cap.get("color", "white"),
                stroke_color=cap.get("stroke_color", "black"),
                stroke_width=cap.get("stroke_width", 2),
            )
            .set_start(cap.get("start", 0))
            .set_duration(cap.get("duration", 3))
            .set_position(("center", cap.get("position", "bottom")))
        )
        layers.append(text_clip)
    return CompositeVideoClip(layers, size=main_clip.size).set_duration(main_clip.duration)


def add_music(main_clip, project_dir: Path, config: dict):
    music_path = find_optional_file(project_dir, "music", AUDIO_EXTENSIONS)
    if music_path is None:
        return main_clip

    music = AudioFileClip(str(music_path))
    volume = config.get("music_volume", 0.2)
    music = music.volumex(volume)

    if music.duration < main_clip.duration:
        loops = int(main_clip.duration // music.duration) + 1
        music = concatenate_audioclips([music] * loops)
    music = music.subclip(0, main_clip.duration)

    final_audio = CompositeAudioClip([main_clip.audio, music]) if main_clip.audio is not None else music
    return main_clip.set_audio(final_audio)


def render_project(project_dir: Path, output_dir: Path, base_config: dict):
    print(f"\n=== Монтаж проекта: {project_dir.name} ===")
    config = load_project_config(project_dir, base_config)

    clip_paths = find_clips(project_dir)
    print(f"Найдено клипов: {len(clip_paths)}")

    clip = build_main_sequence(clip_paths, config)
    clip = add_hook(clip, project_dir)
    clip = add_avatar(clip, project_dir, config)
    clip = add_captions(clip, config)
    clip = add_music(clip, project_dir, config)

    if config.get("resolution"):
        clip = clip.resize(newsize=tuple(config["resolution"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{project_dir.name}.mp4"
    clip.write_videofile(
        str(output_path),
        fps=config.get("fps", 30),
        codec="libx264",
        audio_codec="aac",
    )
    print(f"Готово: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Автоматический монтаж видеороликов")
    parser.add_argument("--project", type=Path, help="Путь к одному проекту (папке с клипами)")
    parser.add_argument("--projects-dir", type=Path, default=Path("projects"), help="Папка со всеми проектами для пакетной обработки")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Куда сохранять готовые ролики")
    parser.add_argument("--all", action="store_true", help="Обработать все проекты в --projects-dir")
    args = parser.parse_args()

    base_config = dict(DEFAULT_CONFIG)
    base_config["avatar"] = dict(DEFAULT_CONFIG["avatar"])
    root_config_path = Path("config.yaml")
    if root_config_path.exists():
        user_config = load_yaml(root_config_path)
        avatar_override = user_config.pop("avatar", None)
        base_config.update(user_config)
        if avatar_override:
            base_config["avatar"].update(avatar_override)

    if args.all:
        if not args.projects_dir.is_dir():
            sys.exit(f"Папка с проектами не найдена: {args.projects_dir}")
        project_dirs = sorted(p for p in args.projects_dir.iterdir() if p.is_dir())
        if not project_dirs:
            sys.exit(f"В папке {args.projects_dir} нет проектов")
        for project_dir in project_dirs:
            render_project(project_dir, args.output_dir, base_config)
    elif args.project:
        render_project(args.project, args.output_dir, base_config)
    else:
        parser.error("Укажите --project <папка> или --all")


if __name__ == "__main__":
    main()
