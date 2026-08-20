from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.config import settings

ALLOWED_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


# TODO: replace local storage with S3-compatible storage


class LocalStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.UPLOAD_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_image(self, upload: UploadFile) -> str:
        mime = (upload.content_type or "").lower()
        if mime not in ALLOWED_MIME:
            raise HTTPException(status_code=400, detail="Разрешены только изображения JPEG, PNG или WebP")
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(0)
        if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Файл больше {settings.MAX_UPLOAD_MB} МБ")
        try:
            img = Image.open(upload.file)
            img.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректный файл изображения")
        upload.file.seek(0)
        img = Image.open(upload.file)
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        filename = f"{uuid4().hex}{ALLOWED_MIME[mime]}"
        dest = self.root / filename
        img.save(dest)
        return filename

    def resolve(self, key: str) -> Path:
        path = (self.root / Path(key).name).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")
        return path


storage = LocalStorage()
