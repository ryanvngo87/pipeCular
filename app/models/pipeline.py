from pydantic import BaseModel
from typing import Optional

class Step(BaseModel):
    name: str
    status: str
    logs: Optional[str] = None
    error_output: Optional[str] = None

class Job(BaseModel):
    name: str
    status: str
    steps: list[Step] = []
    job_id: Optional[str] = None

class PipelineRun(BaseModel):
    platform: str
    run_id: str
    status: str
    jobs: list[Job] = []