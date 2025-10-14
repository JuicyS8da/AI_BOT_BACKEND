# app/common/files.py
from __future__ import annotations

import mimetypes
import secrets
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import UploadFile, Request

# где лежат файлы на диске
MEDIA_ROOT = Path("media")
# публичный префикс (обязательно смонтируй в FastAPI: app.mount("/media", StaticFiles(...)))
MEDIA_URL = "/media"


def _safe_ext(filename: str | None, content_type: str | None) -> str:
    """
    Определить безопасное расширение: сначала из имени, если пусто — из MIME.
    """
    ext = ""
    if filename:
        ext = Path(filename).suffix
    if not ext and content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed:
            ext = guessed
    return ext or ".bin"


async def _async_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)


async def save_file_for_quiz(quiz_id: int, file: UploadFile, filename: Optional[str] = None) -> str:
    """
    Сохраняет файл в media/quizes/<quiz_id>/<filename> и возвращает относительный URL
    вида /media/quizes/<quiz_id>/<filename>.

    Если filename не указан — генерим случайное.
    """
    quiz_dir = MEDIA_ROOT / "quizes" / str(quiz_id)
    quiz_dir.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(file.filename, file.content_type)
    name = filename or f"{secrets.token_hex(8)}{ext}"
    dest = quiz_dir / name

    content = await file.read()
    await _async_write_bytes(dest, content)

    return f"{MEDIA_URL}/quizes/{quiz_id}/{name}"


async def save_files_for_quiz_with_labels(quiz_id: int, files: List[UploadFile]) -> List[str]:
    """
    Сохраняет файлы в media/quizes/<quiz_id>/ с именами A.jpg, B.png, C..., по порядку.
    Возвращает список относительных URL-ов в том же порядке.
    """
    urls: List[str] = []
    for i, f in enumerate(files):
        # A..Z, дальше — extra_<i>
        label = chr(ord("A") + i) if i < 26 else f"extra_{i}"
        ext = _safe_ext(f.filename, f.content_type)
        filename = f"{label}{ext}"
        url = await save_file_for_quiz(quiz_id, f, filename=filename)
        urls.append(url)
    return urls


async def save_upload(request: Request, file: UploadFile, subdir: str) -> str:
    """
    Универсальное сохранение в media/<subdir>/..., возвращает АБСОЛЮТНЫЙ URL.
    Подходит, если нужно вернуть полный URL (например, для фронта на другом домене).
    """
    target_dir = MEDIA_ROOT / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    ext = _safe_ext(file.filename, file.content_type)
    name = f"{secrets.token_hex(8)}{ext}"
    dest = target_dir / name

    content = await file.read()
    await _async_write_bytes(dest, content)

    base = str(request.base_url).rstrip("/")
    return f"{base}{MEDIA_URL}/{subdir}/{name}"

async def _save_uploads(request: Request, files: List[UploadFile], subdir: str = "questions") -> List[str]:
    """
    Сохраняет набор UploadFile в media/<subdir>/ и возвращает СПИСОК ОТНОСИТЕЛЬНЫХ URL’ов:
    [/media/<subdir>/<name1>, /media/<subdir>/<name2>, ...].

    Сигнатура совместима с твоим использованием в сервисе.
    """
    if not files:
        return []

    target_dir = MEDIA_ROOT / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    urls: List[str] = []
    for f in files:
        ext = _safe_ext(f.filename, f.content_type)
        name = f"{secrets.token_hex(8)}{ext}"
        dest = target_dir / name

        content = await f.read()
        await _async_write_bytes(dest, content)

        urls.append(f"{MEDIA_URL}/{subdir}/{name}")

    return urls