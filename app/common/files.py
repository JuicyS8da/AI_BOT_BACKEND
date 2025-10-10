import uuid

from uuid import uuid4

from pathlib import Path
from fastapi import UploadFile, Request
import os, secrets
from typing import List

MEDIA_ROOT = Path("media")
MEDIA_URL = "/media"
MEDIA_PREFIX = "/media"

async def save_file_for_quiz(quiz_id: int, file: UploadFile) -> str:
    folder = MEDIA_ROOT / "quizes" / str(quiz_id)
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    name = f"{uuid4().hex}{ext}"
    dest = folder / name
    dest.write_bytes(await file.read())
    return f"{MEDIA_URL}/quizes/{quiz_id}/{name}"

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

async def _save_uploads(request: Request, files: List[UploadFile], subdir: str = "questions") -> List[str]:
    """
    Сохраняет набор файлов и возвращает ПУБЛИЧНЫЕ URL’ы.
    Предполагается, что StaticFiles смонтирован на MEDIA_PREFIX.
    """
    saved_urls: List[str] = []
    if not files:
        return saved_urls

    base_fs_dir = os.path.join(MEDIA_ROOT, subdir)
    _ensure_dir(base_fs_dir)

    for f in files:
        ext = os.path.splitext(f.filename or "")[1] or ".bin"
        fname = f"{uuid.uuid4().hex}{ext}"
        fs_path = os.path.join(base_fs_dir, fname)

        content = await f.read()
        with open(fs_path, "wb") as out:
            out.write(content)

        # публичный путь
        url_path = f"{MEDIA_PREFIX}/{subdir}/{fname}"
        # абсолютный URL (если хочешь)
        # public_url = str(request.base_url).rstrip('/') + url_path
        saved_urls.append(url_path)

    return saved_urls

async def save_upload(request: Request, file: UploadFile, subdir: str) -> str:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    folder = MEDIA_ROOT / subdir
    folder.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    name = f"{secrets.token_hex(8)}{ext}"
    path = folder / name

    with open(path, "wb") as out:
        out.write(await file.read())

    # Вернём абсолютный URL (на фронт)
    base = str(request.base_url).rstrip("/")
    return f"{base}/media/{subdir}/{name}"