import base64
import time
import structlog
from app.infrastructure.generators.base import VideoGenerator

logger = structlog.get_logger()

# A base64 representation of a tiny valid 1-second blank MP4 video
TINY_MP4_BASE64 = (
    "AAAAHGZ0eXBtcDQyAAAAAG1wNDJpc29tYXZjMQAAAz5mcmVlAAAAG21kYXTeAAAAMmZyZWUAAAA2"
    "bWRhdFj//5BqaDloYWtjdGVtcGxhdGVfZ2VuZXJhdGVkX2J5X2FudGlncmF2aXR5///9621vb3YA"
    "AAxtdmhkAAAAAMw112fMNddnAAAA+gAAAAAAAfQAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARAA"
    "AAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAgN0cmFrAAAAXHRraGQAAAAD"
    "zDXYZ8w112cAAAABAAAAAAAB9AAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAEAAAAAAAAAAAAAAAAAAAAYJtZGlhAAAAJG1kaGQAAAAAzDXYZ8w112cAAAAAAAAB9AAAAV5V"
    "hGhkAAAAKmhkbHIAAAAAAAAAAHZpZGVvAAAAAAAAAAAAAAAAVmlkZW9IYW5kbGVyAAAAAQhtZGlu"
    "ZgAAABB2bWhkAAAAAQAAAAAAAAAAJGRpbmYAAAAcYmxyZAAAAAAAAAAQdXJsIAAAAAEAAAEBc3Ry"
    "YgAAAKBzdHNkAAAAAAAAAAEAdmpzdgAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAgACABIAAAASAAA"
    "AB4AAAAAYXZjMQAAAAAAAAAAAAAAAAAAAAAAAAAAAQAY/+EAGGd2K0yQAqALv/gLcBAQDxIuAEAe"
    "BiICAAADAAEAAAMAMg8UKAEABmguZy4yAAAAHGVzZHMAAAAAAAMEgDBYAAEBh2F2Y2MAAQAC//8A"
    "FHN0dHMAAAAAAAAAAQAAAAEAAAABAAAAKHN0c3oAAAAAAAAADQAAAAEAAAABAAAAAQAAAAEAAAAB"
    "AAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAAUc3RjbwAAAAAAAAABAAAAMAAAAGJ1"
    "ZGsAAABpdWR0YQAAAGF0YWcAAAAyZnJlZQAAAG1kYXQ="
)


class MockGenerator(VideoGenerator):
    def generate(
        self,
        prompt: str,
        duration: int,
        resolution: str,
        fps: int,
        seed: int,
        output_path: str,
    ) -> None:
        logger.info(
            "Starting mock video generation",
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            fps=fps,
            seed=seed,
        )

        # Simulate GPU compute/inference time
        time.sleep(2.0)

        # Decode base64 to target output_path
        try:
            video_data = base64.b64decode(TINY_MP4_BASE64)
            with open(output_path, "wb") as f:
                f.write(video_data)
            logger.info("Mock video generation completed", output_path=output_path)
        except Exception as e:
            logger.error("Failed to write mock video file", error=str(e))
            raise e
