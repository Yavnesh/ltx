from app.infrastructure.storage import get_storage_provider


class StorageService:
    def __init__(self):
        self.provider = get_storage_provider()

    def upload_video(self, local_path: str, filename: str) -> str:
        return self.provider.upload_file(local_path, f"videos/{filename}")

    def delete_video(self, filename: str) -> None:
        self.provider.delete_file(f"videos/{filename}")

    def get_video_url(self, filename: str) -> str:
        return self.provider.get_url(f"videos/{filename}")
