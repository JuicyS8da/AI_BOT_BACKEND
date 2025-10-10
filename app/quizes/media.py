from pathlib import Path

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_CT = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 10 * 1024 * 1024
