from app.workflows.nodes.analyze_root_cause import analyze_root_cause
from app.workflows.nodes.classify_failure import classify_failure
from app.workflows.nodes.detect_platform import detect_platform
from app.workflows.nodes.extract_errors import extract_errors
from app.workflows.nodes.fetch_pipeline import fetch_pipeline
from app.workflows.nodes.generate_report import generate_report
from app.workflows.nodes.parse_input import parse_input
from app.workflows.nodes.retrieve_context import retrieve_context
from app.workflows.nodes.suggest_fix import suggest_fix
from app.workflows.state import WorkflowState

_PIPELINE = [
    parse_input,       # 1 — extract run URL/ID
    detect_platform,   # 2 — verify platform is supported
    fetch_pipeline,    # 3+4 — fetch + normalize to PipelineRun
    extract_errors,    # 5 — fetch logs, populate error_output
    classify_failure,  # 6 — categorize failure type
    retrieve_context,  # 7 — fetch relevant source files
    analyze_root_cause,# 8 — LLM root cause hypothesis
    suggest_fix,       # 9 — LLM fix suggestions
    generate_report,   # 10 — emit markdown report
]


def run_pipeline(raw_input: str) -> WorkflowState:
    state: WorkflowState = {"raw_input": raw_input}
    for node in _PIPELINE:
        state = node(state)
    return state
