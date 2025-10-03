from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, Request, HTTPException, status

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_CT = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 10 * 1024 * 1024

def _ext_by_ct(ct: str) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(ct, "")

async def _save_upload(request: Request, file: UploadFile) -> str:
    if file.content_type not in ALLOWED_CT:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="unsupported_media_type")
    ext = Path(file.filename or "").suffix.lower() or _ext_by_ct(file.content_type)
    if not ext:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_detect_extension")

    fname = f"{uuid4().hex}{ext}"
    dest = MEDIA_DIR / fname

    size = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_too_large")
                f.write(chunk)
    finally:
        await file.close()

    return str(request.url_for("media", path=fname))
