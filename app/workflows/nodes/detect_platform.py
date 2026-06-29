from app.workflows.state import WorkflowState

KNOWN_PLATFORMS = {"github_actions"}


def detect_platform(state: WorkflowState) -> WorkflowState:
    platform = state.get("platform", "unknown")

    if platform in KNOWN_PLATFORMS:
        return state

    raise ValueError(
        f"Cannot detect CI platform from run ID {state.get('run_id')!r}. "
        "Provide a full pipeline URL instead."
    )
