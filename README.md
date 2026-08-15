# Монтаж видеороликов

Скрипт на Python (MoviePy + FFmpeg) для автоматической сборки роликов из
клипов: склейка, обрезка, переходы, хук в начале, аватар поверх видео
(picture-in-picture), текстовые подписи и фоновая музыка. Поддерживает
пакетную обработку сразу нескольких проектов из одной папки.

## Установка

1. Установите FFmpeg (нужен MoviePy для чтения/записи видео):
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: `choco install ffmpeg` или скачать с ffmpeg.org и добавить в PATH

2. Создайте виртуальное окружение и поставьте зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Структура проекта

Каждый ролик — это папка внутри `projects/`:

```
projects/
  my_video/
    clips/            # исходные клипы — склеиваются в порядке имён файлов
      01_intro.mp4     #   (поэтому называйте файлы с числовым префиксом)
      02_main.mp4
      03_outro.mp4
    hook.mp4            # необязательно — приклеивается в самое начало
    avatar.mp4|.png     # необязательно — оверлей в углу видео (PiP)
    music.mp3            # необязательно — фоновая музыка
    config.yaml           # необязательно — настройки именно этого проекта
```

Пример уже лежит в `projects/example/` — положите туда свои видео в
`clips/` и запустите скрипт.

## Настройки (config.yaml)

Общие настройки по умолчанию лежат в `config.example.yaml` — скопируйте
его в `config.yaml` в корне репозитория, чтобы задать значения для всех
проектов сразу. Любое поле можно переопределить внутри конкретного
проекта в `projects/<name>/config.yaml` — см. пример в
`projects/example/config.yaml`.

Доступные поля:

| Поле | Описание |
|---|---|
| `transition_duration` | длительность кроссфейда между клипами, сек (0 — жёсткая склейка без перехода) |
| `trim` | список обрезок конкретных файлов: `{file, start, end}` в секундах |
| `resolution` | итоговое разрешение `[ширина, высота]`, например `[1080, 1920]` для вертикального видео |
| `fps` | частота кадров результата |
| `music_volume` | громкость фоновой музыки, 0.0–1.0 |
| `font` | путь к `.ttf` шрифту для подписей (если не задан — берётся системный) |
| `captions` | список подписей: `{text, start, duration, position, font_size, color}`. Требует установленного [ImageMagick](https://imagemagick.org/script/download.php) — без него не используйте эту секцию |
| `avatar.position` | угол размещения: `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `avatar.width_ratio` | ширина аватара относительно ширины видео |
| `avatar.margin` | отступ от края кадра, px |

## Запуск

Один проект:
```bash
python montage.py --project projects/my_video
```

Все проекты в `projects/` сразу:
```bash
python montage.py --all
```

Готовые ролики сохраняются в `output/<имя_проекта>.mp4`. Путь к папкам
можно поменять флагами `--projects-dir` и `--output-dir`.
