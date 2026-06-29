from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.generate_report import generate_report

_FAILED_STEP = Step(name="Run tests", status="failure", error_output="##[error]2 tests failed")
_SUCCESS_STEP = Step(name="Checkout", status="success")
_FAILED_JOB = Job(name="build", status="failure", steps=[_SUCCESS_STEP, _FAILED_STEP])
_SUCCESS_JOB = Job(name="lint", status="success", steps=[_SUCCESS_STEP])

_FULL_PIPELINE = PipelineRun(
    platform="github_actions",
    run_id="42",
    status="failure",
    jobs=[_FAILED_JOB, _SUCCESS_JOB],
)

_FULL_STATE = {
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
    "pipeline_run": _FULL_PIPELINE,
    "failure_category": "test_failure",
    "root_cause": "The test asserts 1 == 2 which is always false.",
    "suggested_fix": "Fix the assertion to match the actual expected value.",
}


def test_report_set_in_state():
    result = generate_report(_FULL_STATE)
    assert isinstance(result["report"], str)
    assert len(result["report"]) > 0


def test_report_contains_repo_info():
    result = generate_report(_FULL_STATE)
    report = result["report"]
    assert "octocat/hello-world" in report
    assert "42" in report
    assert "github_actions" in report


def test_report_contains_failed_job():
    result = generate_report(_FULL_STATE)
    assert "build" in result["report"]


def test_report_contains_failed_step():
    result = generate_report(_FULL_STATE)
    assert "Run tests" in result["report"]


def test_report_contains_error_snippet():
    result = generate_report(_FULL_STATE)
    assert "##[error]2 tests failed" in result["report"]


def test_report_contains_classification():
    result = generate_report(_FULL_STATE)
    assert "test_failure" in result["report"]


def test_report_contains_root_cause():
    result = generate_report(_FULL_STATE)
    assert "The test asserts 1 == 2" in result["report"]


def test_report_contains_suggested_fix():
    result = generate_report(_FULL_STATE)
    assert "Fix the assertion" in result["report"]


def test_report_handles_missing_root_cause():
    state = {**_FULL_STATE, "root_cause": None}
    result = generate_report(state)
    assert "_Not analyzed_" in result["report"]


def test_report_handles_missing_suggested_fix():
    state = {**_FULL_STATE, "suggested_fix": None}
    result = generate_report(state)
    assert "_No suggestions available_" in result["report"]


def test_report_handles_no_pipeline_run():
    state = {**_FULL_STATE, "pipeline_run": None}
    result = generate_report(state)
    assert "unknown" in result["report"]


def test_existing_state_fields_preserved():
    result = generate_report(_FULL_STATE)
    assert result["owner"] == "octocat"
    assert result["failure_category"] == "test_failure"


def test_successful_jobs_not_in_failed_section():
    result = generate_report(_FULL_STATE)
    # "lint" is a successful job — it should not appear under Failed Jobs
    report = result["report"]
    failed_section_start = report.index("## Failed Jobs")
    classification_start = report.index("## Failure Classification")
    failed_section = report[failed_section_start:classification_start]
    assert "lint" not in failed_section
