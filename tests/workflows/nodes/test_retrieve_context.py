from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.retrieve_context import _extract_file_paths, retrieve_context

_BASE_STATE = {
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
}


def _make_pipeline(error_output: str | None) -> PipelineRun:
    step = Step(name="Run tests", status="failure", error_output=error_output)
    job = Job(name="build", status="failure", job_id="7", steps=[step])
    return PipelineRun(platform="github_actions", run_id="42", status="failure", jobs=[job])


def _patch_svc(files: dict[str, str]):
    svc = MagicMock()
    svc.__enter__ = MagicMock(return_value=svc)
    svc.__exit__ = MagicMock(return_value=False)
    svc.get_file_content.side_effect = lambda owner, repo, path: files[path]
    return patch("app.workflows.nodes.retrieve_context.GitHubService", return_value=svc)


# --- _extract_file_paths unit tests ---

def test_extracts_pytest_failed_path():
    text = "FAILED tests/utils/test_url_parser.py::test_github_actions_url"
    assert _extract_file_paths(text) == ["tests/utils/test_url_parser.py"]


def test_extracts_traceback_path():
    text = 'File "app/utils/url_parser.py", line 42, in parse_url'
    assert _extract_file_paths(text) == ["app/utils/url_parser.py"]


def test_deduplicates_paths():
    text = (
        "FAILED tests/test_foo.py::test_a\n"
        "FAILED tests/test_foo.py::test_b"
    )
    assert _extract_file_paths(text) == ["tests/test_foo.py"]


def test_returns_empty_for_no_paths():
    assert _extract_file_paths("##[error]build failed") == []


def test_caps_at_five_files():
    lines = "\n".join(f"FAILED tests/test_{i}.py::test_x" for i in range(10))
    result = _extract_file_paths(lines)
    assert len(result) == 5


# --- retrieve_context node tests ---

def test_no_pipeline_run_returns_empty_context():
    state = {**_BASE_STATE, "pipeline_run": None}
    result = retrieve_context(state)
    assert result["repo_context"] == {}


def test_no_file_paths_in_errors_returns_empty_context():
    pipeline = _make_pipeline("##[error]something failed")
    state = {**_BASE_STATE, "pipeline_run": pipeline}
    result = retrieve_context(state)
    assert result["repo_context"] == {}


def test_fetches_file_content_for_referenced_paths():
    pipeline = _make_pipeline("FAILED tests/test_foo.py::test_bar")
    state = {**_BASE_STATE, "pipeline_run": pipeline}

    with _patch_svc({"tests/test_foo.py": "def test_bar(): assert False"}):
        result = retrieve_context(state)

    assert result["repo_context"]["tests/test_foo.py"] == "def test_bar(): assert False"


def test_missing_file_silently_skipped():
    pipeline = _make_pipeline("FAILED tests/test_foo.py::test_bar\nFAILED tests/test_bar.py::test_x")
    state = {**_BASE_STATE, "pipeline_run": pipeline}

    svc = MagicMock()
    svc.__enter__ = MagicMock(return_value=svc)
    svc.__exit__ = MagicMock(return_value=False)
    svc.get_file_content.side_effect = lambda o, r, p: (
        "content" if p == "tests/test_foo.py" else (_ for _ in ()).throw(httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock()))
    )

    with patch("app.workflows.nodes.retrieve_context.GitHubService", return_value=svc):
        result = retrieve_context(state)

    assert "tests/test_foo.py" in result["repo_context"]
    assert "tests/test_bar.py" not in result["repo_context"]


def test_existing_state_fields_preserved():
    pipeline = _make_pipeline("##[error]no paths here")
    state = {**_BASE_STATE, "pipeline_run": pipeline}
    result = retrieve_context(state)
    assert result["owner"] == "octocat"
    assert result["run_id"] == "42"
