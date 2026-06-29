from app.adapters.base import BaseAdapter
from app.models.pipeline import Job, PipelineRun, Step
from app.services.github_service import GitHubService

_STATUS_MAP = {
    "success": "success",
    "failure": "failure",
    "cancelled": "failure",
    "timed_out": "failure",
    "action_required": "failure",
    "skipped": "skipped",
    "neutral": "success",
    "in_progress": "running",
    "queued": "queued",
    "waiting": "queued",
    "pending": "queued",
}


def _normalize_status(raw: str | None) -> str:
    if not raw:
        return "unknown"
    return _STATUS_MAP.get(raw, raw)


def _build_step(step: dict) -> Step:
    status = _normalize_status(step.get("conclusion") or step.get("status"))
    return Step(name=step["name"], status=status)


def _build_job(job: dict) -> Job:
    status = _normalize_status(job.get("conclusion") or job.get("status"))
    steps = [_build_step(s) for s in job.get("steps", [])]
    return Job(name=job["name"], status=status, steps=steps, job_id=str(job["id"]) if job.get("id") else None)


class GitHubActionsAdapter(BaseAdapter):
    def __init__(self, service: GitHubService):
        self._service = service

    def fetch_and_normalize(self, owner: str, repo: str, run_id: str) -> PipelineRun:
        run_data = self._service.get_run(owner, repo, run_id)
        jobs_data = self._service.get_run_jobs(owner, repo, run_id)

        run_status = _normalize_status(
            run_data.get("conclusion") or run_data.get("status")
        )
        jobs = [_build_job(j) for j in jobs_data.get("jobs", [])]

        return PipelineRun(
            platform="github_actions",
            run_id=run_id,
            status=run_status,
            jobs=jobs,
        )
