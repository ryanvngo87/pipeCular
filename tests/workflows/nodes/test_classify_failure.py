import pytest

from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.classify_failure import classify_failure

_BASE_STATE = {
    "raw_input": "https://github.com/octocat/hello-world/actions/runs/42",
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
}


def _make_pipeline(job_name: str, error_output: str | None = None) -> PipelineRun:
    step = Step(name="run", status="failure", error_output=error_output)
    job = Job(name=job_name, status="failure", steps=[step])
    return PipelineRun(platform="github_actions", run_id="42", status="failure", jobs=[job])


def _state_with(job_name: str, error_output: str | None = None) -> dict:
    return {**_BASE_STATE, "pipeline_run": _make_pipeline(job_name, error_output)}


# --- error-output pattern matching ---

def test_classifies_test_failure_pytest():
    state = _state_with("build", "FAILED tests/test_foo.py::test_bar - AssertionError")
    result = classify_failure(state)
    assert result["failure_category"] == "test_failure"


def test_classifies_test_failure_count():
    state = _state_with("ci", "##[error]3 tests failed")
    result = classify_failure(state)
    assert result["failure_category"] == "test_failure"


def test_classifies_dependency_error_module_not_found():
    state = _state_with("build", "ModuleNotFoundError: No module named 'requests'")
    result = classify_failure(state)
    assert result["failure_category"] == "dependency_error"


def test_classifies_dependency_error_pip():
    state = _state_with("setup", "pip: error: could not find a version")
    result = classify_failure(state)
    assert result["failure_category"] == "dependency_error"


def test_classifies_build_error_syntax():
    state = _state_with("build", "SyntaxError: invalid syntax")
    result = classify_failure(state)
    assert result["failure_category"] == "build_error"


def test_classifies_build_error_typescript():
    state = _state_with("build", "error TS2304: Cannot find name 'foo'")
    result = classify_failure(state)
    assert result["failure_category"] == "build_error"


def test_classifies_lint_error_flake8():
    state = _state_with("check", "flake8: E501 line too long")
    result = classify_failure(state)
    assert result["failure_category"] == "lint_error"


def test_classifies_lint_error_eslint():
    state = _state_with("check", "eslint: error  'foo' is not defined")
    result = classify_failure(state)
    assert result["failure_category"] == "lint_error"


def test_classifies_timeout():
    state = _state_with("build", "##[error]The operation timed out")
    result = classify_failure(state)
    assert result["failure_category"] == "timeout"


def test_classifies_infrastructure_oom():
    state = _state_with("build", "##[error]Out of memory: Kill process")
    result = classify_failure(state)
    assert result["failure_category"] == "infrastructure"


# --- job-name hint fallback (no error_output) ---

def test_falls_back_to_job_name_test():
    state = _state_with("Run tests", error_output=None)
    result = classify_failure(state)
    assert result["failure_category"] == "test_failure"


def test_falls_back_to_job_name_lint():
    state = _state_with("lint", error_output=None)
    result = classify_failure(state)
    assert result["failure_category"] == "lint_error"


def test_falls_back_to_job_name_build():
    state = _state_with("build", error_output=None)
    result = classify_failure(state)
    assert result["failure_category"] == "build_error"


def test_falls_back_to_job_name_install():
    state = _state_with("install dependencies", error_output=None)
    result = classify_failure(state)
    assert result["failure_category"] == "dependency_error"


# --- unknown / edge cases ---

def test_unknown_when_nothing_matches():
    state = _state_with("ci", error_output=None)
    result = classify_failure(state)
    assert result["failure_category"] == "unknown"


def test_no_pipeline_run_returns_unknown():
    state = {**_BASE_STATE, "pipeline_run": None}
    result = classify_failure(state)
    assert result["failure_category"] == "unknown"
    assert result["failure_reason"] == "no pipeline data"


def test_reason_contains_error_text():
    error = "FAILED tests/test_foo.py::test_bar"
    state = _state_with("build", error)
    result = classify_failure(state)
    assert error in result["failure_reason"]


def test_reason_truncated_to_500_chars():
    long_error = "FAILED tests/test_foo.py::test_bar " * 30
    state = _state_with("build", long_error)
    result = classify_failure(state)
    assert len(result["failure_reason"]) <= 500


def test_existing_state_fields_preserved():
    state = _state_with("build", "FAILED tests/test_foo.py::test_bar")
    result = classify_failure(state)
    assert result["platform"] == "github_actions"
    assert result["owner"] == "octocat"
    assert result["run_id"] == "42"


def test_error_output_takes_priority_over_job_name():
    # Job is named "test" (→ test_failure hint) but error_output says timeout
    state = _state_with("Run tests", "The operation timed out")
    result = classify_failure(state)
    assert result["failure_category"] == "timeout"
