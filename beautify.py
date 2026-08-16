#!/usr/bin/env python3
"""Сглаживание кожи + лёгкий тон губ и румянец на лице в видео.

Находит лицо на каждом кадре (через MediaPipe Face Mesh) и аккуратно
обрабатывает только кожу — глаза, брови и губы остаются чёткими.

Это самая тяжёлая по вычислениям операция из всего набора скриптов —
обрабатывается покадрово, поэтому на слабом компьютере может идти
заметно медленнее, чем сам ролик длится. Лучше сначала попробовать на
одном коротком файле.

Запуск для одного файла:
    python beautify.py "output/interview_highlights/01_smehoterapiya.mp4" "output/beautified/01_smehoterapiya.mp4"

Запуск для целой папки (обработает все .mp4 внутри):
    python beautify.py --batch "output/interview_highlights" "output/beautified"
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import cv2
import imageio_ffmpeg
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh


def _connections_to_points(connections):
    idxs = set()
    for a, b in connections:
        idxs.add(a)
        idxs.add(b)
    return sorted(idxs)


OVAL_IDX = _connections_to_points(mp_face_mesh.FACEMESH_FACE_OVAL)
LIPS_IDX = _connections_to_points(mp_face_mesh.FACEMESH_LIPS)
EXCLUDE_SETS = [
    mp_face_mesh.FACEMESH_LEFT_EYE,
    mp_face_mesh.FACEMESH_RIGHT_EYE,
    mp_face_mesh.FACEMESH_LEFT_EYEBROW,
    mp_face_mesh.FACEMESH_RIGHT_EYEBROW,
    mp_face_mesh.FACEMESH_LIPS,
]
CHEEK_LANDMARKS = [50, 280]


def beautify_frame(img: np.ndarray, face_mesh) -> np.ndarray:
    h, w = img.shape[:2]
    results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        return img

    lm = results.multi_face_landmarks[0]
    pts = np.array([(p.x * w, p.y * h) for p in lm.landmark], dtype=np.float32)

    face_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(face_mask, cv2.convexHull(pts[OVAL_IDX].astype(np.int32)), 255)
    for conn in EXCLUDE_SETS:
        idx = _connections_to_points(conn)
        cv2.fillConvexPoly(face_mask, cv2.convexHull(pts[idx].astype(np.int32)), 0)

    mask_blur = cv2.GaussianBlur(face_mask, (21, 21), 0).astype(np.float32) / 255.0
    mask_blur3 = np.dstack([mask_blur] * 3)
    smooth = cv2.bilateralFilter(img, d=15, sigmaColor=50, sigmaSpace=15)
    result = img.astype(np.float32) * (1 - mask_blur3) + smooth.astype(np.float32) * mask_blur3

    lips_hull = cv2.convexHull(pts[LIPS_IDX].astype(np.int32))
    lip_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(lip_mask, lips_hull, 255)
    lip_mask = cv2.GaussianBlur(lip_mask, (7, 7), 0).astype(np.float32) / 255.0 * 0.18
    lip_mask3 = np.dstack([lip_mask] * 3)
    lip_color = np.full_like(result, (90, 80, 180))
    result = result * (1 - lip_mask3) + lip_color * lip_mask3

    for idx in CHEEK_LANDMARKS:
        cx, cy = int(pts[idx][0]), int(pts[idx][1])
        cheek_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(cheek_mask, (cx, cy), int(w * 0.06), 255, -1)
        cheek_mask = cv2.GaussianBlur(cheek_mask, (31, 31), 0).astype(np.float32) / 255.0 * 0.15
        cheek_mask3 = np.dstack([cheek_mask] * 3)
        blush_color = np.full_like(result, (110, 110, 220))
        result = result * (1 - cheek_mask3) + blush_color * cheek_mask3

    return np.clip(result, 0, 255).astype(np.uint8)


def beautify_video(input_path: Path, output_path: Path) -> None:
    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_video = output_path.with_suffix(".noaudio.mp4")
    writer = cv2.VideoWriter(str(tmp_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    start = time.time()
    n = 0
    with mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True) as fm:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(beautify_frame(frame, fm))
            n += 1
            if n % 50 == 0:
                elapsed = time.time() - start
                print(f"  {n}/{total} кадров, {elapsed:.0f} сек, {n/elapsed:.1f} fps")
    cap.release()
    writer.release()
    print(f"  Обработано {n} кадров за {time.time()-start:.0f} сек")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-i", str(tmp_video), "-i", str(input_path),
        "-c:v", "libx264", "-map", "0:v:0", "-map", "1:a:0?",
        "-shortest", str(output_path),
    ]
    subprocess.run(cmd, check=True)
    tmp_video.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сглаживание лица + лёгкий макияж на видео")
    parser.add_argument("input", type=Path, help="Видеофайл или (с --batch) папка с видео")
    parser.add_argument("output", type=Path, help="Куда сохранить результат (файл или папка)")
    parser.add_argument("--batch", action="store_true", help="Обработать все .mp4 файлы в папке input")
    args = parser.parse_args()

    if args.batch:
        if not args.input.is_dir():
            sys.exit(f"Папка не найдена: {args.input}")
        videos = sorted(args.input.glob("*.mp4"))
        if not videos:
            sys.exit(f"В папке {args.input} нет .mp4 файлов")
        args.output.mkdir(parents=True, exist_ok=True)
        for i, video in enumerate(videos, start=1):
            print(f"\n[{i}/{len(videos)}] {video.name}")
            beautify_video(video, args.output / video.name)
        print(f"\nГотово! Результаты в: {args.output}")
    else:
        if not args.input.exists():
            sys.exit(f"Файл не найден: {args.input}")
        print(f"Обрабатываю {args.input.name}...")
        beautify_video(args.input, args.output)
        print(f"Готово: {args.output}")


if __name__ == "__main__":
    main()
