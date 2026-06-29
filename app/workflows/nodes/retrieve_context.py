import os
import re

from app.models.pipeline import PipelineRun
from app.services.github_service import GitHubService
from app.workflows.state import WorkflowState

_PYTEST_FAILED_RE = re.compile(r"FAILED\s+([\w/.+-]+\.py)::")
_TRACEBACK_FILE_RE = re.compile(r'File\s+"([\w/.+-]+\.py)"')
_MAX_FILES = 5


def _extract_file_paths(error_text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for pattern in (_PYTEST_FAILED_RE, _TRACEBACK_FILE_RE):
        for m in pattern.finditer(error_text):
            p = m.group(1)
            if p not in seen:
                seen.add(p)
                paths.append(p)
    return paths[:_MAX_FILES]


def _collect_error_text(pipeline_run: PipelineRun) -> str:
    parts = []
    for job in pipeline_run.jobs:
        if job.status == "failure":
            for step in job.steps:
                if step.status == "failure" and step.error_output:
                    parts.append(step.error_output)
    return "\n".join(parts)


def retrieve_context(state: WorkflowState) -> WorkflowState:
    pipeline_run = state.get("pipeline_run")
    if not pipeline_run:
        return {**state, "repo_context": {}}

    error_text = _collect_error_text(pipeline_run)
    file_paths = _extract_file_paths(error_text)

    if not file_paths:
        return {**state, "repo_context": {}}

    owner = state.get("owner", "")
    repo = state.get("repo", "")
    repo_context: dict[str, str] = {}

    with GitHubService(token=os.environ.get("GITHUB_TOKEN")) as svc:
        for path in file_paths:
            try:
                repo_context[path] = svc.get_file_content(owner, repo, path)
            except Exception:
                pass

    return {**state, "repo_context": repo_context}
