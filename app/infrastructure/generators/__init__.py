from app.infrastructure.config import settings
from app.infrastructure.generators.base import VideoGenerator
from app.infrastructure.generators.mock import MockGenerator
from app.infrastructure.generators.ltx import LTXGenerator


def get_video_generator() -> VideoGenerator:
    gen_type = settings.GENERATOR_TYPE.lower()
    if gen_type == "mock":
        return MockGenerator()
    elif gen_type == "ltx":
        return LTXGenerator(model_path=settings.LTX_MODEL_PATH)
    else:
        raise ValueError(f"Unknown generator type: {gen_type}")
