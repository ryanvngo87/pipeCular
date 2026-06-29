from typing import Optional, TypedDict

from app.models.pipeline import PipelineRun


class WorkflowState(TypedDict, total=False):
    raw_input: str
    platform: str
    run_id: str
    owner: str
    repo: str
    pipeline_run: Optional[PipelineRun]
    failure_category: str
    failure_reason: str
    repo_context: dict[str, str]
    root_cause: str
    suggested_fix: str
    report: Optional[str]
