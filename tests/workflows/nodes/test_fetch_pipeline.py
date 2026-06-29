import pytest
from unittest.mock import MagicMock, patch

from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.fetch_pipeline import fetch_pipeline, _get_adapter

_GITHUB_STATE = {
    "raw_input": "https://github.com/octocat/hello-world/actions/runs/42",
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
}

_SAMPLE_RUN = PipelineRun(
    platform="github_actions",
    run_id="42",
    status="failure",
    jobs=[
        Job(
            name="build",
            status="failure",
            steps=[
                Step(name="Checkout", status="success"),
                Step(name="Run tests", status="failure"),
            ],
        )
    ],
)


def _mock_adapter(pipeline_run=_SAMPLE_RUN):
    adapter = MagicMock()
    adapter.fetch_and_normalize.return_value = pipeline_run
    return adapter


def test_pipeline_run_set_in_state():
    with patch("app.workflows.nodes.fetch_pipeline._get_adapter", return_value=_mock_adapter()):
        result = fetch_pipeline(_GITHUB_STATE)
    assert result["pipeline_run"] == _SAMPLE_RUN


def test_existing_state_fields_preserved():
    with patch("app.workflows.nodes.fetch_pipeline._get_adapter", return_value=_mock_adapter()):
        result = fetch_pipeline(_GITHUB_STATE)
    assert result["platform"] == "github_actions"
    assert result["owner"] == "octocat"
    assert result["repo"] == "hello-world"
    assert result["run_id"] == "42"


def test_fetch_and_normalize_called_with_correct_args():
    adapter = _mock_adapter()
    with patch("app.workflows.nodes.fetch_pipeline._get_adapter", return_value=adapter):
        fetch_pipeline(_GITHUB_STATE)
    adapter.fetch_and_normalize.assert_called_once_with("octocat", "hello-world", "42")


def test_unknown_platform_raises():
    state = {**_GITHUB_STATE, "platform": "circleci"}
    with pytest.raises(ValueError, match="No adapter registered"):
        fetch_pipeline(state)


def test_get_adapter_returns_github_adapter_for_github_actions():
    from app.adapters.github_actions import GitHubActionsAdapter
    adapter = _get_adapter("github_actions")
    assert isinstance(adapter, GitHubActionsAdapter)


def test_get_adapter_raises_for_unknown_platform():
    with pytest.raises(ValueError, match="No adapter registered"):
        _get_adapter("jenkins")
