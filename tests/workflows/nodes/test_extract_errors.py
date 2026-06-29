import pytest
from unittest.mock import MagicMock, patch

from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.extract_errors import extract_errors

_FAILED_STEP = Step(name="Run tests", status="failure")
_SUCCESS_STEP = Step(name="Checkout", status="success")

_FAILED_JOB = Job(name="build", status="failure", job_id="7", steps=[_SUCCESS_STEP, _FAILED_STEP])
_SUCCESS_JOB = Job(name="lint", status="success", job_id="8", steps=[_SUCCESS_STEP])

_PIPELINE_FAILURE = PipelineRun(
    platform="github_actions",
    run_id="42",
    status="failure",
    jobs=[_FAILED_JOB, _SUCCESS_JOB],
)

_BASE_STATE = {
    "raw_input": "https://github.com/octocat/hello-world/actions/runs/42",
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
    "pipeline_run": _PIPELINE_FAILURE,
}

_SAMPLE_LOG = (
    "2024-01-01T00:00:01.000Z Running pytest...\n"
    "2024-01-01T00:00:02.000Z ##[error]2 tests failed\n"
    "2024-01-01T00:00:03.000Z FAILED tests/test_foo.py::test_bar\n"
)


def _patch_logs(logs: dict[int, str]):
    svc = MagicMock()
    svc.__enter__ = MagicMock(return_value=svc)
    svc.__exit__ = MagicMock(return_value=False)
    svc.get_job_logs.side_effect = lambda owner, repo, job_id: logs[job_id]
    return patch("app.workflows.nodes.extract_errors.GitHubService", return_value=svc)


def test_returns_state_unchanged_if_no_pipeline_run():
    state = {**_BASE_STATE, "pipeline_run": None}
    result = extract_errors(state)
    assert result["pipeline_run"] is None


def test_failed_step_gets_error_output():
    with _patch_logs({7: _SAMPLE_LOG}):
        result = extract_errors(_BASE_STATE)
    failed_step = result["pipeline_run"].jobs[0].steps[1]
    assert failed_step.status == "failure"
    assert "##[error]2 tests failed" in failed_step.error_output
    assert "FAILED tests/test_foo.py::test_bar" in failed_step.error_output


def test_successful_step_not_modified():
    with _patch_logs({7: _SAMPLE_LOG}):
        result = extract_errors(_BASE_STATE)
    success_step = result["pipeline_run"].jobs[0].steps[0]
    assert success_step.status == "success"
    assert success_step.error_output is None


def test_successful_job_logs_not_fetched():
    svc = MagicMock()
    svc.__enter__ = MagicMock(return_value=svc)
    svc.__exit__ = MagicMock(return_value=False)
    svc.get_job_logs.return_value = _SAMPLE_LOG

    with patch("app.workflows.nodes.extract_errors.GitHubService", return_value=svc):
        extract_errors(_BASE_STATE)

    fetched_ids = [call.args[2] for call in svc.get_job_logs.call_args_list]
    assert 8 not in fetched_ids


def test_job_without_job_id_skipped():
    job_no_id = Job(name="build", status="failure", job_id=None, steps=[_FAILED_STEP])
    pipeline = PipelineRun(platform="github_actions", run_id="1", status="failure", jobs=[job_no_id])
    state = {**_BASE_STATE, "pipeline_run": pipeline}

    svc = MagicMock()
    svc.__enter__ = MagicMock(return_value=svc)
    svc.__exit__ = MagicMock(return_value=False)

    with patch("app.workflows.nodes.extract_errors.GitHubService", return_value=svc):
        result = extract_errors(state)

    svc.get_job_logs.assert_not_called()
    assert result["pipeline_run"].jobs[0].steps[0].error_output is None


def test_existing_state_fields_preserved():
    with _patch_logs({7: _SAMPLE_LOG}):
        result = extract_errors(_BASE_STATE)
    assert result["platform"] == "github_actions"
    assert result["owner"] == "octocat"
    assert result["run_id"] == "42"


def test_unsupported_platform_raises():
    pipeline = PipelineRun(platform="circleci", run_id="1", status="failure", jobs=[])
    state = {**_BASE_STATE, "platform": "circleci", "pipeline_run": pipeline}
    with pytest.raises(ValueError, match="unsupported platform"):
        extract_errors(state)
