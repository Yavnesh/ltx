from abc import ABC, abstractmethod


class VideoGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration: int,
        resolution: str,
        fps: int,
        seed: int,
        output_path: str,
    ) -> None:
        """Generate a video based on the parameters and write it to output_path."""
        pass
