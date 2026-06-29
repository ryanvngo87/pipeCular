import pytest
from unittest.mock import MagicMock

from app.adapters.github_actions import GitHubActionsAdapter, _normalize_status
from app.models.pipeline import PipelineRun


def _make_adapter(run_data=None, jobs_data=None):
    svc = MagicMock()
    svc.get_run.return_value = run_data or {}
    svc.get_run_jobs.return_value = jobs_data or {"jobs": []}
    return GitHubActionsAdapter(service=svc)


_RUN_SUCCESS = {"status": "completed", "conclusion": "success"}
_RUN_FAILURE = {"status": "completed", "conclusion": "failure"}
_RUN_IN_PROGRESS = {"status": "in_progress", "conclusion": None}

_JOB_FAILED = {
    "name": "build",
    "status": "completed",
    "conclusion": "failure",
    "steps": [
        {"name": "Checkout", "status": "completed", "conclusion": "success"},
        {"name": "Run tests", "status": "completed", "conclusion": "failure"},
    ],
}

_JOB_SUCCESS = {
    "name": "lint",
    "status": "completed",
    "conclusion": "success",
    "steps": [],
}


# --- _normalize_status unit tests ---

def test_normalize_success():
    assert _normalize_status("success") == "success"


def test_normalize_failure():
    assert _normalize_status("failure") == "failure"


def test_normalize_cancelled_maps_to_failure():
    assert _normalize_status("cancelled") == "failure"


def test_normalize_timed_out_maps_to_failure():
    assert _normalize_status("timed_out") == "failure"


def test_normalize_in_progress_maps_to_running():
    assert _normalize_status("in_progress") == "running"


def test_normalize_queued():
    assert _normalize_status("queued") == "queued"


def test_normalize_skipped():
    assert _normalize_status("skipped") == "skipped"


def test_normalize_none_returns_unknown():
    assert _normalize_status(None) == "unknown"


def test_normalize_empty_string_returns_unknown():
    assert _normalize_status("") == "unknown"


# --- GitHubActionsAdapter.fetch_and_normalize tests ---

def test_returns_pipeline_run_instance():
    adapter = _make_adapter(_RUN_SUCCESS)
    result = adapter.fetch_and_normalize("octocat", "hello-world", "42")
    assert isinstance(result, PipelineRun)


def test_run_id_and_platform_set():
    adapter = _make_adapter(_RUN_SUCCESS)
    result = adapter.fetch_and_normalize("octocat", "hello-world", "42")
    assert result.run_id == "42"
    assert result.platform == "github_actions"


def test_successful_run_status():
    adapter = _make_adapter(_RUN_SUCCESS)
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.status == "success"


def test_failed_run_status():
    adapter = _make_adapter(_RUN_FAILURE)
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.status == "failure"


def test_in_progress_run_uses_status_field():
    adapter = _make_adapter(_RUN_IN_PROGRESS)
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.status == "running"


def test_conclusion_takes_priority_over_status():
    # conclusion is set → use it, not status
    run_data = {"status": "completed", "conclusion": "failure"}
    adapter = _make_adapter(run_data)
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.status == "failure"


def test_jobs_are_mapped():
    adapter = _make_adapter(_RUN_FAILURE, {"jobs": [_JOB_FAILED, _JOB_SUCCESS]})
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert len(result.jobs) == 2
    assert result.jobs[0].name == "build"
    assert result.jobs[1].name == "lint"


def test_job_status_normalized():
    adapter = _make_adapter(_RUN_FAILURE, {"jobs": [_JOB_FAILED]})
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.jobs[0].status == "failure"


def test_steps_are_mapped():
    adapter = _make_adapter(_RUN_FAILURE, {"jobs": [_JOB_FAILED]})
    result = adapter.fetch_and_normalize("o", "r", "1")
    steps = result.jobs[0].steps
    assert len(steps) == 2
    assert steps[0].name == "Checkout"
    assert steps[0].status == "success"
    assert steps[1].name == "Run tests"
    assert steps[1].status == "failure"


def test_empty_jobs_list():
    adapter = _make_adapter(_RUN_SUCCESS, {"jobs": []})
    result = adapter.fetch_and_normalize("o", "r", "1")
    assert result.jobs == []


def test_service_called_with_correct_args():
    svc = MagicMock()
    svc.get_run.return_value = _RUN_SUCCESS
    svc.get_run_jobs.return_value = {"jobs": []}
    adapter = GitHubActionsAdapter(service=svc)

    adapter.fetch_and_normalize("octocat", "hello-world", "99")

    svc.get_run.assert_called_once_with("octocat", "hello-world", "99")
    svc.get_run_jobs.assert_called_once_with("octocat", "hello-world", "99")
