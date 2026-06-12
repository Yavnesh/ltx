from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, local_path: str, object_name: str) -> str:
        """Upload a file to storage and return its accessible URL."""
        pass

    @abstractmethod
    def download_file(self, object_name: str, dest_path: str) -> None:
        """Download a file from storage to local path."""
        pass

    @abstractmethod
    def delete_file(self, object_name: str) -> None:
        """Delete a file from storage."""
        pass

    @abstractmethod
    def get_url(self, object_name: str) -> str:
        """Get the public/presigned URL of the object."""
        pass
