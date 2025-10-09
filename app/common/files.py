from uuid import uuid4
from pathlib import Path
from fastapi import UploadFile, Request

MEDIA_ROOT = Path("media")
MEDIA_URL = "/media"

async def save_file_for_quiz(quiz_id: int, file: UploadFile) -> str:
    folder = MEDIA_ROOT / "quizes" / str(quiz_id)
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    name = f"{uuid4().hex}{ext}"
    dest = folder / name
    dest.write_bytes(await file.read())
    return f"{MEDIA_URL}/quizes/{quiz_id}/{name}"

async def _save_upload(request: Request, file: UploadFile) -> str:
    quiz_id = request.query_params.get("quiz_id") or "common"
    folder = MEDIA_ROOT / "quizes" / str(quiz_id)
    folder.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix or ""
    filename = f"{uuid4().hex}{ext}"
    dest = folder / filename
    dest.write_bytes(await file.read())

    return f"{MEDIA_URL}/quizes/{quiz_id}/{filename}"