from unittest.mock import MagicMock, patch

from app.models.pipeline import Job, PipelineRun, Step
from app.workflows.nodes.analyze_root_cause import _build_prompt, analyze_root_cause

_BASE_STATE = {
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
    "failure_category": "test_failure",
    "failure_reason": "FAILED tests/test_foo.py::test_bar - AssertionError",
    "repo_context": {"tests/test_foo.py": "def test_bar():\n    assert 1 == 2"},
    "pipeline_run": PipelineRun(
        platform="github_actions",
        run_id="42",
        status="failure",
        jobs=[
            Job(
                name="build",
                status="failure",
                steps=[Step(name="Run tests", status="failure")],
            )
        ],
    ),
}


def _mock_anthropic(text: str):
    content_block = MagicMock()
    content_block.text = text
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    return patch("app.workflows.nodes.analyze_root_cause.anthropic.Anthropic", return_value=client)


def test_root_cause_set_in_state():
    with _mock_anthropic("The assertion `1 == 2` is always false."):
        result = analyze_root_cause(_BASE_STATE)
    assert result["root_cause"] == "The assertion `1 == 2` is always false."


def test_existing_state_fields_preserved():
    with _mock_anthropic("some cause"):
        result = analyze_root_cause(_BASE_STATE)
    assert result["failure_category"] == "test_failure"
    assert result["owner"] == "octocat"


def test_prompt_contains_failure_category():
    prompt = _build_prompt(_BASE_STATE)
    assert "test_failure" in prompt


def test_prompt_contains_error_output():
    prompt = _build_prompt(_BASE_STATE)
    assert "test_foo.py" in prompt


def test_prompt_contains_repo_context():
    prompt = _build_prompt(_BASE_STATE)
    assert "tests/test_foo.py" in prompt
    assert "assert 1 == 2" in prompt


def test_prompt_contains_repo_name():
    prompt = _build_prompt(_BASE_STATE)
    assert "octocat/hello-world" in prompt


def test_prompt_handles_missing_optional_fields():
    state = {"platform": "github_actions", "run_id": "1", "owner": "o", "repo": "r"}
    prompt = _build_prompt(state)
    assert "unknown" in prompt


def test_llm_called_with_correct_model():
    with _mock_anthropic("cause") as mock_cls:
        analyze_root_cause(_BASE_STATE)
    mock_cls.return_value.messages.create.assert_called_once()
    call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_response_is_stripped():
    with _mock_anthropic("  root cause with whitespace  "):
        result = analyze_root_cause(_BASE_STATE)
    assert result["root_cause"] == "root cause with whitespace"
