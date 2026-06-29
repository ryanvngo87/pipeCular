import os

from app.models.pipeline import PipelineRun
from app.services.github_service import GitHubService
from app.services.log_parser_service import extract_error_context
from app.workflows.state import WorkflowState


def _fetch_logs_github(pipeline_run: PipelineRun, owner: str, repo: str) -> dict[str, str]:
    logs: dict[str, str] = {}
    with GitHubService(token=os.environ.get("GITHUB_TOKEN")) as svc:
        for job in pipeline_run.jobs:
            if job.status == "failure" and job.job_id:
                logs[job.job_id] = svc.get_job_logs(owner, repo, int(job.job_id))
    return logs


def extract_errors(state: WorkflowState) -> WorkflowState:
    pipeline_run = state.get("pipeline_run")
    if not pipeline_run:
        return state

    platform = state["platform"]
    if platform == "github_actions":
        raw_logs = _fetch_logs_github(
            pipeline_run,
            state.get("owner", ""),
            state.get("repo", ""),
        )
    else:
        raise ValueError(f"extract_errors: unsupported platform {platform!r}")

    updated_jobs = []
    for job in pipeline_run.jobs:
        log_text = raw_logs.get(job.job_id or "")
        if not log_text:
            updated_jobs.append(job)
            continue

        error_output = extract_error_context(log_text)
        updated_steps = [
            step.model_copy(update={"error_output": error_output})
            if step.status == "failure"
            else step
            for step in job.steps
        ]
        updated_jobs.append(job.model_copy(update={"steps": updated_steps}))

    updated_run = pipeline_run.model_copy(update={"jobs": updated_jobs})
    return {**state, "pipeline_run": updated_run}
