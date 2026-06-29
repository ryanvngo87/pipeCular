import re

from app.models.pipeline import PipelineRun
from app.workflows.state import WorkflowState

_CATEGORY_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("timeout", [
        re.compile(r"timed[_\s-]?out", re.IGNORECASE),
        re.compile(r"timeout exceeded", re.IGNORECASE),
    ]),
    ("dependency_error", [
        re.compile(r"ModuleNotFoundError"),
        re.compile(r"No module named"),
        re.compile(r"npm ERR!"),
        re.compile(r"Could not find a version that satisfies"),
        re.compile(r"pip.*\berror\b", re.IGNORECASE),
    ]),
    ("test_failure", [
        re.compile(r"\bFAILED\b.+\.py"),
        re.compile(r"\bAssertionError\b"),
        re.compile(r"\d+ tests? failed"),
        re.compile(r"pytest.*\bfailed\b", re.IGNORECASE),
    ]),
    ("build_error", [
        re.compile(r"\bSyntaxError\b"),
        re.compile(r"\bBuild failed\b", re.IGNORECASE),
        re.compile(r"\berror TS\d+\b"),
        re.compile(r"\bcannot find symbol\b", re.IGNORECASE),
    ]),
    ("lint_error", [
        re.compile(r"\bflake8\b"),
        re.compile(r"\beslint\b", re.IGNORECASE),
        re.compile(r"\bruff\b.*\berror\b", re.IGNORECASE),
        re.compile(r"\bmypy\b.*\berror\b", re.IGNORECASE),
    ]),
    ("infrastructure", [
        re.compile(r"no space left on device", re.IGNORECASE),
        re.compile(r"out of memory", re.IGNORECASE),
        re.compile(r"runner.*lost", re.IGNORECASE),
    ]),
]

_JOB_NAME_HINTS: list[tuple[str, re.Pattern]] = [
    ("test_failure",     re.compile(r"\btests?\b", re.IGNORECASE)),
    ("lint_error",       re.compile(r"\b(lint|format|style)\b", re.IGNORECASE)),
    ("build_error",      re.compile(r"\b(build|compile)\b", re.IGNORECASE)),
    ("dependency_error", re.compile(r"\b(install|dep|dependencies)\b", re.IGNORECASE)),
]


def _collect_error_text(pipeline_run: PipelineRun) -> str:
    parts = []
    for job in pipeline_run.jobs:
        if job.status == "failure":
            for step in job.steps:
                if step.status == "failure" and step.error_output:
                    parts.append(step.error_output)
    return "\n".join(parts)


def _classify_by_error_text(text: str) -> str | None:
    for category, patterns in _CATEGORY_PATTERNS:
        if any(p.search(text) for p in patterns):
            return category
    return None


def _classify_by_job_names(pipeline_run: PipelineRun) -> str | None:
    for job in pipeline_run.jobs:
        if job.status == "failure":
            for category, pattern in _JOB_NAME_HINTS:
                if pattern.search(job.name):
                    return category
    return None


def classify_failure(state: WorkflowState) -> WorkflowState:
    pipeline_run = state.get("pipeline_run")
    if not pipeline_run:
        return {**state, "failure_category": "unknown", "failure_reason": "no pipeline data"}

    error_text = _collect_error_text(pipeline_run)
    category = (
        _classify_by_error_text(error_text)
        or _classify_by_job_names(pipeline_run)
        or "unknown"
    )
    reason = error_text[:500] if error_text else "no error output available"

    return {**state, "failure_category": category, "failure_reason": reason}
