import os

from app.adapters.github_actions import GitHubActionsAdapter
from app.services.github_service import GitHubService
from app.workflows.state import WorkflowState


def _get_adapter(platform: str):
    if platform == "github_actions":
        return GitHubActionsAdapter(service=GitHubService(token=os.environ.get("GITHUB_TOKEN")))
    raise ValueError(f"No adapter registered for platform: {platform!r}")


def fetch_pipeline(state: WorkflowState) -> WorkflowState:
    adapter = _get_adapter(state["platform"])
    pipeline_run = adapter.fetch_and_normalize(
        state.get("owner", ""),
        state.get("repo", ""),
        state["run_id"],
    )
    return {**state, "pipeline_run": pipeline_run}
