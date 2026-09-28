from dataclasses import dataclass, field

@dataclass
class Job:
    number: int
    prompt: str
    first_image: str = ""
    last_image: str = ""
    mode: str = "text_to_video"
    model: str = "veo_31_lite"
    aspect_ratio: str = "9:16"
    resolution: list[str] = field(default_factory=lambda: ["720p"])
    video_length: int = 8
    name: str = ""
    status: str = "Chờ"
    task_id: str = ""
    result: list[str] = field(default_factory=list)
    error: str = ""
