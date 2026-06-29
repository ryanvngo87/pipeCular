import os

from app.models.pipeline import PipelineRun
from app.services.github_service import GitHubService
from app.services.log_parser_service import extract_error_context, split_log_by_step
from app.workflows.state import WorkflowState


def _fetch_logs_github(pipeline_run: PipelineRun, owner: str, repo: str) -> dict[str, str]:
    logs: dict[str, str] = {}
    with GitHubService(token=os.environ.get("GITHUB_TOKEN")) as svc:
        for job in pipeline_run.jobs:
            if job.status == "failure" and job.job_id:
                logs[job.job_id] = svc.get_job_logs(owner, repo, int(job.job_id))
    return logs


def _find_step_log(step_name: str, step_logs: dict[str, str]) -> str | None:
    lower = step_name.lower()
    for name, text in step_logs.items():
        if name.lower() == lower:
            return text
    return None


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

        step_logs = split_log_by_step(log_text)
        job_error_output = extract_error_context(log_text)

        updated_steps = []
        for step in job.steps:
            if step.status != "failure":
                updated_steps.append(step)
                continue

            step_log = _find_step_log(step.name, step_logs)
            if step_log is not None:
                error_output = extract_error_context(step_log) or job_error_output
                updated_steps.append(
                    step.model_copy(update={"logs": step_log, "error_output": error_output})
                )
            else:
                updated_steps.append(
                    step.model_copy(update={"error_output": job_error_output})
                )

        updated_jobs.append(job.model_copy(update={"steps": updated_steps}))

    updated_run = pipeline_run.model_copy(update={"jobs": updated_jobs})
    return {**state, "pipeline_run": updated_run}
