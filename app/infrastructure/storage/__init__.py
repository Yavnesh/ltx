from app.infrastructure.config import settings
from app.infrastructure.storage.base import StorageProvider
from app.infrastructure.storage.local import LocalStorageProvider
from app.infrastructure.storage.s3 import S3StorageProvider


def get_storage_provider() -> StorageProvider:
    provider_type = settings.STORAGE_PROVIDER_TYPE.lower()
    if provider_type == "local":
        return LocalStorageProvider(base_path=settings.STORAGE_LOCAL_PATH)
    elif provider_type in ("minio", "s3"):
        return S3StorageProvider(
            bucket_name=settings.STORAGE_BUCKET_NAME,
            endpoint_url=settings.STORAGE_ENDPOINT_URL,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION,
        )
    else:
        raise ValueError(f"Unknown storage provider type: {provider_type}")
