import pytest

from app.workflows.nodes.detect_platform import detect_platform


def test_known_platform_passes_through():
    state = {"raw_input": "https://github.com/octocat/hello-world/actions/runs/1", "platform": "github_actions", "run_id": "1", "owner": "octocat", "repo": "hello-world"}
    result = detect_platform(state)
    assert result["platform"] == "github_actions"


def test_unknown_platform_raises():
    state = {"raw_input": "9876543210", "platform": "unknown", "run_id": "9876543210"}
    with pytest.raises(ValueError, match="Cannot detect CI platform"):
        detect_platform(state)


def test_missing_platform_raises():
    state = {"raw_input": "9876543210", "run_id": "9876543210"}
    with pytest.raises(ValueError, match="Cannot detect CI platform"):
        detect_platform(state)


def test_state_fields_preserved():
    state = {"raw_input": "https://github.com/octocat/hello-world/actions/runs/1", "platform": "github_actions", "run_id": "1", "owner": "octocat", "repo": "hello-world", "report": None}
    result = detect_platform(state)
    assert result["report"] is None
    assert result["owner"] == "octocat"
