import pytest

from app.workflows.nodes.parse_input import parse_input


def test_github_url_populates_state():
    state = {"raw_input": "https://github.com/octocat/hello-world/actions/runs/9876543210"}
    result = parse_input(state)
    assert result["platform"] == "github_actions"
    assert result["run_id"] == "9876543210"
    assert result["owner"] == "octocat"
    assert result["repo"] == "hello-world"


def test_bare_run_id_populates_state():
    state = {"raw_input": "9876543210"}
    result = parse_input(state)
    assert result["platform"] == "unknown"
    assert result["run_id"] == "9876543210"


def test_existing_state_fields_preserved():
    state = {"raw_input": "https://github.com/octocat/hello-world/actions/runs/1", "report": None}
    result = parse_input(state)
    assert "report" in result
    assert result["report"] is None


def test_raw_input_preserved_in_result():
    state = {"raw_input": "https://github.com/octocat/hello-world/actions/runs/1"}
    result = parse_input(state)
    assert result["raw_input"] == state["raw_input"]


def test_invalid_url_raises():
    state = {"raw_input": "https://unknown-ci.io/runs/42"}
    with pytest.raises(ValueError):
        parse_input(state)
