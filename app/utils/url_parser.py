import re
from urllib.parse import urlparse

from pydantic import BaseModel


class ParsedInput(BaseModel):
    platform: str
    run_id: str
    owner: str = ""
    repo: str = ""


_GITHUB_RUNS_RE = re.compile(
    r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/actions/runs/(?P<run_id>\d+)"
)


def parse_url(raw_input: str) -> ParsedInput:
    raw = raw_input.strip()

    if "/" not in raw:
        return ParsedInput(platform="unknown", run_id=raw)

    parsed = urlparse(raw)
    netloc = parsed.netloc.lower()

    if netloc in ("github.com", "www.github.com"):
        return _parse_github(parsed.path)

    raise ValueError(f"Unrecognized CI platform URL: {raw!r}")


def _parse_github(path: str) -> ParsedInput:
    m = _GITHUB_RUNS_RE.match(path)
    if not m:
        raise ValueError(
            f"URL does not match GitHub Actions runs format "
            f"(expected /{{owner}}/{{repo}}/actions/runs/{{run_id}}): {path!r}"
        )
    return ParsedInput(
        platform="github_actions",
        run_id=m.group("run_id"),
        owner=m.group("owner"),
        repo=m.group("repo"),
    )
