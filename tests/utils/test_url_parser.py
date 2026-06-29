import pytest

from app.utils.url_parser import ParsedInput, parse_url


def test_github_actions_url():
    result = parse_url("https://github.com/octocat/hello-world/actions/runs/9876543210")
    assert result.platform == "github_actions"
    assert result.run_id == "9876543210"
    assert result.owner == "octocat"
    assert result.repo == "hello-world"


def test_github_url_with_job_segment():
    result = parse_url("https://github.com/octocat/hello-world/actions/runs/9876543210/jobs/123")
    assert result.platform == "github_actions"
    assert result.run_id == "9876543210"
    assert result.owner == "octocat"
    assert result.repo == "hello-world"


def test_www_github_url():
    result = parse_url("https://www.github.com/octocat/hello-world/actions/runs/42")
    assert result.platform == "github_actions"
    assert result.run_id == "42"


def test_bare_run_id():
    result = parse_url("9876543210")
    assert result.platform == "unknown"
    assert result.run_id == "9876543210"
    assert result.owner == ""
    assert result.repo == ""


def test_whitespace_stripped():
    result = parse_url("  9876543210  ")
    assert result.run_id == "9876543210"


def test_unknown_platform_raises():
    with pytest.raises(ValueError, match="Unrecognized CI platform URL"):
        parse_url("https://unknown-ci.io/runs/42")


def test_github_wrong_path_raises():
    with pytest.raises(ValueError, match="does not match GitHub Actions runs format"):
        parse_url("https://github.com/octocat/hello-world/pull/99")


def test_returns_parsed_input_model():
    result = parse_url("https://github.com/octocat/hello-world/actions/runs/1")
    assert isinstance(result, ParsedInput)
