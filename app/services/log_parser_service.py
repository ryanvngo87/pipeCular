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
