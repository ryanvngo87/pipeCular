from app.services.log_parser_service import extract_error_context, split_log_by_step


def test_extracts_github_error_annotation():
    log = "2024-01-01T00:00:01.000Z ##[error]Process completed with exit code 1."
    result = extract_error_context(log)
    assert "##[error]Process completed with exit code 1." in result


def test_extracts_failed_test_line():
    log = "2024-01-01T00:00:01.000Z FAILED tests/test_foo.py::test_bar - AssertionError"
    result = extract_error_context(log)
    assert "FAILED tests/test_foo.py::test_bar" in result


def test_extracts_error_keyword():
    log = "2024-01-01T00:00:01.000Z Error: Cannot find module './missing'"
    result = extract_error_context(log)
    assert "Error: Cannot find module './missing'" in result


def test_error_keyword_case_insensitive():
    log = "2024-01-01T00:00:01.000Z error: something went wrong"
    result = extract_error_context(log)
    assert "error: something went wrong" in result


def test_extracts_exception_line():
    log = "2024-01-01T00:00:01.000Z Exception: null pointer"
    result = extract_error_context(log)
    assert "Exception: null pointer" in result


def test_extracts_traceback_line():
    log = "2024-01-01T00:00:01.000Z Traceback (most recent call last):"
    result = extract_error_context(log)
    assert "Traceback (most recent call last):" in result


def test_strips_timestamps():
    log = "2024-01-01T00:00:01.0000000Z ##[error]build failed"
    result = extract_error_context(log)
    assert result == "##[error]build failed"


def test_empty_log_returns_empty_string():
    assert extract_error_context("") == ""


def test_no_errors_returns_empty_string():
    log = "2024-01-01T00:00:01.000Z Step passed successfully.\n2024-01-01T00:00:02.000Z All good."
    assert extract_error_context(log) == ""


def test_multiple_error_lines_joined():
    log = (
        "2024-01-01T00:00:01.000Z ##[error]first error\n"
        "2024-01-01T00:00:02.000Z some noise\n"
        "2024-01-01T00:00:03.000Z ##[error]second error"
    )
    result = extract_error_context(log)
    assert result == "##[error]first error\n##[error]second error"


def test_caps_at_max_lines():
    lines = "\n".join(f"2024-01-01T00:00:0{i}.000Z ##[error]err {i}" for i in range(30))
    result = extract_error_context(lines, max_lines=5)
    assert len(result.splitlines()) == 5


# --- split_log_by_step ---

_GROUPED_LOG = (
    "2024-01-01T00:00:01.000Z ##[group]Checkout\n"
    "2024-01-01T00:00:02.000Z Cloning repository...\n"
    "2024-01-01T00:00:03.000Z ##[endgroup]\n"
    "2024-01-01T00:00:04.000Z ##[group]Run tests\n"
    "2024-01-01T00:00:05.000Z ##[error]2 tests failed\n"
    "2024-01-01T00:00:06.000Z FAILED tests/test_foo.py::test_bar\n"
    "2024-01-01T00:00:07.000Z ##[endgroup]\n"
)


def test_splits_into_named_sections():
    result = split_log_by_step(_GROUPED_LOG)
    assert set(result.keys()) == {"Checkout", "Run tests"}


def test_section_content_correct():
    result = split_log_by_step(_GROUPED_LOG)
    assert "Cloning repository..." in result["Checkout"]
    assert "##[error]2 tests failed" in result["Run tests"]
    assert "FAILED tests/test_foo.py::test_bar" in result["Run tests"]


def test_group_markers_not_in_section_content():
    result = split_log_by_step(_GROUPED_LOG)
    assert "##[group]" not in result["Checkout"]
    assert "##[endgroup]" not in result["Checkout"]


def test_timestamps_stripped_from_section_content():
    result = split_log_by_step(_GROUPED_LOG)
    assert "2024-01-01T" not in result["Checkout"]


def test_lines_outside_groups_discarded():
    log = (
        "2024-01-01T00:00:01.000Z pre-step noise\n"
        "2024-01-01T00:00:02.000Z ##[group]Step A\n"
        "2024-01-01T00:00:03.000Z inside step\n"
        "2024-01-01T00:00:04.000Z ##[endgroup]\n"
        "2024-01-01T00:00:05.000Z post-step noise\n"
    )
    result = split_log_by_step(log)
    assert "pre-step noise" not in "\n".join(result.values())
    assert "post-step noise" not in "\n".join(result.values())
    assert "inside step" in result["Step A"]


def test_empty_log_returns_empty_dict():
    assert split_log_by_step("") == {}


def test_log_with_no_group_markers_returns_empty_dict():
    log = "2024-01-01T00:00:01.000Z ##[error]something failed\n"
    assert split_log_by_step(log) == {}


def test_handles_unclosed_group():
    log = (
        "2024-01-01T00:00:01.000Z ##[group]Run tests\n"
        "2024-01-01T00:00:02.000Z ##[error]build failed\n"
    )
    result = split_log_by_step(log)
    assert "Run tests" in result
    assert "##[error]build failed" in result["Run tests"]


def test_multiple_steps_content_isolated():
    result = split_log_by_step(_GROUPED_LOG)
    assert "Cloning repository..." not in result["Run tests"]
    assert "##[error]2 tests failed" not in result["Checkout"]
