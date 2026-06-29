import re

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s+")

_ERROR_PATTERNS = [
    re.compile(r"##\[error\]"),
    re.compile(r"\bError:", re.IGNORECASE),
    re.compile(r"\bFAILED\b"),
    re.compile(r"\bException\b"),
    re.compile(r"\bTraceback\b"),
]


def extract_error_context(log_text: str, max_lines: int = 20) -> str:
    """Return condensed error lines from raw GitHub Actions log text."""
    error_lines = []
    for raw_line in log_text.splitlines():
        line = _TIMESTAMP_RE.sub("", raw_line).strip()
        if any(p.search(line) for p in _ERROR_PATTERNS):
            error_lines.append(line)
    return "\n".join(error_lines[:max_lines])


def split_log_by_step(log_text: str) -> dict[str, str]:
    """Parse a GitHub Actions job log into {step_name: log_section} segments.

    GitHub wraps each step's output in ##[group]<name> / ##[endgroup] markers.
    Lines outside any group (pre-step setup noise) are discarded.
    """
    steps: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for raw_line in log_text.splitlines():
        line = _TIMESTAMP_RE.sub("", raw_line)
        if "##[group]" in line:
            if current_name is not None:
                steps[current_name] = "\n".join(current_lines)
            current_name = line.split("##[group]", 1)[1].strip()
            current_lines = []
        elif "##[endgroup]" in line:
            if current_name is not None:
                steps[current_name] = "\n".join(current_lines)
            current_name = None
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        steps[current_name] = "\n".join(current_lines)

    return steps
