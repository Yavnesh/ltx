import os
import shutil
from pathlib import Path

import structlog

from app.infrastructure.storage.base import StorageProvider

logger = structlog.get_logger()


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized LocalStorageProvider", base_path=str(self.base_path))

    def upload_file(self, local_path: str, object_name: str) -> str:
        dest_path = self.base_path / object_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        logger.info("Uploaded file locally", src=local_path, dest=str(dest_path))
        return self.get_url(object_name)

    def download_file(self, object_name: str, dest_path: str) -> None:
        src_path = self.base_path / object_name
        if not src_path.exists():
            raise FileNotFoundError(f"File {object_name} not found in local storage.")
        shutil.copy2(src_path, dest_path)
        logger.info("Downloaded file locally", src=str(src_path), dest=dest_path)

    def delete_file(self, object_name: str) -> None:
        file_path = self.base_path / object_name
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file locally", path=str(file_path))
        else:
            logger.warning("File not found for deletion", path=str(file_path))

    def get_url(self, object_name: str) -> str:
        # We serve this via /static route mounted on the API
        return f"/static/{object_name}"
