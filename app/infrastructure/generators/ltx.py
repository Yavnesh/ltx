import structlog
from app.infrastructure.generators.base import VideoGenerator

logger = structlog.get_logger()


class LTXGenerator(VideoGenerator):
    def __init__(self, model_path: str):
        self.model_path = model_path
        logger.info("Initialized LTXGenerator", model_path=model_path)

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
            "Loading LTX Video Pipeline (lazy-load)",
            model_path=self.model_path,
            prompt=prompt,
        )

        # Import ML libraries inside method to avoid import errors on CPU-only machines
        import torch
        from diffusers import LTXVideoPipeline
        from diffusers.utils import export_to_video

        # Map resolution to width and height
        # LTX is optimized for certain aspect ratios
        width, height = 768, 512
        if resolution == "720p":
            width, height = 1280, 720
        elif resolution == "480p":
            width, height = 848, 480
        elif resolution == "360p":
            width, height = 640, 360

        # Calculate number of frames (fps * duration + 1)
        num_frames = int(fps * duration) + 1

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if device == "cuda" else torch.float32

        logger.info(
            "Running model inference",
            device=device,
            dtype=str(dtype),
            resolution=f"{width}x{height}",
            num_frames=num_frames,
        )

        # Load pipeline
        pipe = LTXVideoPipeline.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
        )
        pipe.to(device)

        if device == "cuda":
            # Enable CPU offload to save VRAM if needed
            pipe.enable_model_cpu_offload()

        # Set seed
        generator = torch.Generator(device=device).manual_seed(seed)

        # Generate frames
        # LTX Video has specific prompt constraints and parameters
        output = pipe(
            prompt=prompt,
            negative_prompt="worst quality, low quality, deformed, distorted",
            width=width,
            height=height,
            num_frames=num_frames,
            fps=fps,
            generator=generator,
            num_inference_steps=25,
        )

        video_frames = output.frames[0]

        # Export to target output path
        export_to_video(video_frames, output_path, fps=fps)
        logger.info("LTX video generation complete", output_path=output_path)
