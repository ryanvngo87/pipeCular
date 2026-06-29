# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**pipeCular** is a CI/CD pipeline failure analyzer. Given a pipeline run URL or ID, it produces a diagnostic report: which stage/job/step failed, a root cause hypothesis, and suggested fixes with relevant code references.

## Setup

```bash
pip install -r requirements.txt
pip install pytest
```

Required environment variables:
- `GITHUB_TOKEN` — GitHub personal access token (read:repo scope). Optional for public repos.
- `ANTHROPIC_API_KEY` — Anthropic API key for the LLM analysis nodes.

## Usage

```bash
python -m app.main <github-actions-url-or-run-id>
# e.g. python -m app.main https://github.com/octocat/hello-world/actions/runs/12345678
```

## Running Tests

```bash
python -m pytest tests/ -v          # full suite (135 tests)
python -m pytest tests/utils/ -v    # single directory
python -m pytest -k parse_github    # by name pattern
```

Or use the `/test` project skill, which wraps the same command.

## Architecture

### 10-Node Workflow

Analysis flows through a sequential node graph (`app/workflows/graph.py`). `run_pipeline(raw_input)` threads `WorkflowState` through every node and returns the final state.

| # | Node | File | Description |
|---|------|------|-------------|
| 1 | Parse Input | `nodes/parse_input.py` | Extract run URL/ID → `platform`, `run_id`, `owner`, `repo` |
| 2 | Detect Platform | `nodes/detect_platform.py` | Verify platform is in the supported set |
| 3+4 | Fetch + Normalize Pipeline | `nodes/fetch_pipeline.py` | Call platform API via adapter → `pipeline_run` |
| 5 | Extract Errors | `nodes/extract_errors.py` | Fetch job logs, populate `error_output` on failed steps |
| 6 | Classify Failure | `nodes/classify_failure.py` | Regex pattern match → `failure_category`, `failure_reason` |
| 7 | Retrieve Context | `nodes/retrieve_context.py` | Fetch referenced source files from GitHub → `repo_context` |
| 8 | Analyze Root Cause | `nodes/analyze_root_cause.py` | LLM call → `root_cause` |
| 9 | Suggest Fix | `nodes/suggest_fix.py` | LLM call → `suggested_fix` |
| 10 | Generate Report | `nodes/generate_report.py` | Assemble markdown → `report` |

All paths above are relative to `app/workflows/`.

### WorkflowState (`app/workflows/state.py`)

Shared `TypedDict` (all fields optional) passed between every node:

| Field | Set by | Type |
|-------|--------|------|
| `raw_input` | caller | `str` |
| `platform` | parse_input | `str` |
| `run_id` | parse_input | `str` |
| `owner` | parse_input | `str` |
| `repo` | parse_input | `str` |
| `pipeline_run` | fetch_pipeline | `PipelineRun \| None` |
| `failure_category` | classify_failure | `str` |
| `failure_reason` | classify_failure | `str` |
| `repo_context` | retrieve_context | `dict[str, str]` |
| `root_cause` | analyze_root_cause | `str` |
| `suggested_fix` | suggest_fix | `str` |
| `report` | generate_report | `str \| None` |

### Adapter Pattern (`app/adapters/`)

`base.py` defines `BaseAdapter` with one abstract method:
```python
def fetch_and_normalize(self, owner: str, repo: str, run_id: str) -> PipelineRun
```

`github_actions.py` implements it: calls `GitHubService.get_run` + `get_run_jobs`, maps GitHub API responses to `PipelineRun`/`Job`/`Step`. Status normalization lives in `_STATUS_MAP` and `_normalize_status`.

### Data Models (`app/models/pipeline.py`)

All Pydantic `BaseModel` subclasses:

- `Step` — `name`, `status`, optional `logs`/`error_output`
- `Job` — `name`, `status`, list of `Step`s, optional `job_id` (GitHub integer ID as string, used for log fetching)
- `PipelineRun` — `platform`, `run_id`, `status`, list of `Job`s

### Service Layer (`app/services/`)

- `github_service.py` — `GitHubService(token?)`: wraps `httpx.Client`. Methods: `get_run`, `get_run_jobs`, `get_job_logs`, `get_file_content`. Supports context-manager usage.
- `log_parser_service.py` — `extract_error_context(log_text)`: strips GitHub timestamps, extracts lines matching error patterns (`##[error]`, `Error:`, `FAILED`, `Exception`, `Traceback`), returns up to 20 joined as a string.

### Utils (`app/utils/url_parser.py`)

- `parse_url(raw_input) -> ParsedInput` — strips whitespace, dispatches by hostname
- `ParsedInput` — Pydantic model with `platform`, `run_id`, `owner`, `repo`
- Bare run IDs (no `/`) return `platform="unknown"`; callers handle platform detection separately
- Unrecognized URLs raise `ValueError`

### LLM Nodes

Both `analyze_root_cause` and `suggest_fix` call `claude-sonnet-4-6` via the `anthropic` SDK. The client is created per call from `ANTHROPIC_API_KEY`. Prompts include the failure category, error output, failed job/step names, and any retrieved source file content (capped at 2000 chars per file).

### Failure Classification (`nodes/classify_failure.py`)

Two-pass heuristic — no LLM:
1. Regex patterns against `error_output` text (timeout checked first to avoid false positives)
2. Fallback: job name hints (e.g. job named "Run tests" → `test_failure`)

Categories: `test_failure`, `dependency_error`, `build_error`, `lint_error`, `timeout`, `infrastructure`, `unknown`.

## Adding a New CI Platform

1. Create `app/adapters/<platform>.py` inheriting from `BaseAdapter`
2. Implement `fetch_and_normalize` — normalize to `PipelineRun` (populate `job_id` on each `Job`)
3. Add a hostname branch in `app/utils/url_parser.py` → `parse_url()`
4. Update `detect_platform.py` `KNOWN_PLATFORMS` set
5. Add the platform's log-fetching branch in `extract_errors.py` and `retrieve_context.py`
6. Add `get_file_content`-equivalent to its service if needed
