from app.utils.url_parser import parse_url
from app.workflows.state import WorkflowState


def parse_input(state: WorkflowState) -> WorkflowState:
    result = parse_url(state["raw_input"])
    return {
        **state,
        "platform": result.platform,
        "run_id": result.run_id,
        "owner": result.owner,
        "repo": result.repo,
    }
