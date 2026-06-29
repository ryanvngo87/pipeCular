from unittest.mock import MagicMock, patch

from app.workflows.nodes.suggest_fix import _build_prompt, suggest_fix

_BASE_STATE = {
    "platform": "github_actions",
    "run_id": "42",
    "owner": "octocat",
    "repo": "hello-world",
    "failure_category": "test_failure",
    "failure_reason": "FAILED tests/test_foo.py::test_bar",
    "root_cause": "The assertion compares incompatible types.",
    "repo_context": {"tests/test_foo.py": "def test_bar():\n    assert 1 == '1'"},
}


def _mock_anthropic(text: str):
    content_block = MagicMock()
    content_block.text = text
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    return patch("app.workflows.nodes.suggest_fix.anthropic.Anthropic", return_value=client)


def test_suggested_fix_set_in_state():
    with _mock_anthropic("1. Cast to int before comparing."):
        result = suggest_fix(_BASE_STATE)
    assert result["suggested_fix"] == "1. Cast to int before comparing."


def test_existing_state_fields_preserved():
    with _mock_anthropic("fix"):
        result = suggest_fix(_BASE_STATE)
    assert result["root_cause"] == "The assertion compares incompatible types."
    assert result["owner"] == "octocat"


def test_prompt_contains_root_cause():
    prompt = _build_prompt(_BASE_STATE)
    assert "The assertion compares incompatible types." in prompt


def test_prompt_contains_error_output():
    prompt = _build_prompt(_BASE_STATE)
    assert "test_foo.py" in prompt


def test_prompt_contains_repo_context():
    prompt = _build_prompt(_BASE_STATE)
    assert "assert 1 == '1'" in prompt


def test_prompt_handles_missing_root_cause():
    state = {**_BASE_STATE, "root_cause": None}
    prompt = _build_prompt(state)
    assert "Unknown" in prompt


def test_llm_called_with_correct_model():
    with _mock_anthropic("fix") as mock_cls:
        suggest_fix(_BASE_STATE)
    call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_response_is_stripped():
    with _mock_anthropic("  fix suggestion  "):
        result = suggest_fix(_BASE_STATE)
    assert result["suggested_fix"] == "fix suggestion"
