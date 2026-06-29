# pipeCular

A pipeline-agnostic CI/CD failure analyzer. Given a pipeline run URL or ID, it produces a diagnostic report identifying what failed, why, and how to fix it.

## Input / Output

**Input:** Pipeline run URL or bare run ID

**Output:**
- Failed stage / job / step
- Error summary
- Root cause hypothesis
- Suggested fix
- Relevant file/code references from the repo
- Optional PR comment or issue creation

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:

```bash
export GITHUB_TOKEN=<your-token>        # GitHub PAT (read:repo). Optional for public repos.
export ANTHROPIC_API_KEY=<your-key>     # Required for root cause + fix suggestions.
```

## Usage

```bash
python -m app.main <pipeline-url-or-run-id>

# Example
python -m app.main https://github.com/owner/repo/actions/runs/12345678
```

## Node Flow

| # | Node | Description |
|---|------|-------------|
| 1 | Parse Input | Extract run URL or ID → platform, run ID, owner, repo |
| 2 | Detect Platform | Verify the platform is supported |
| 3 | Fetch Pipeline | Call the platform API to retrieve run + job data |
| 4 | Normalize Pipeline | Map raw API response to the shared `PipelineRun` model |
| 5 | Extract Error Context | Fetch job logs; isolate error output on failed steps |
| 6 | Classify Failure | Categorize the failure type via pattern matching |
| 7 | Retrieve Repository Context | Fetch relevant source files referenced in the error |
| 8 | Analyze Root Cause | LLM-based root cause hypothesis |
| 9 | Suggest Fix | LLM-based actionable fix suggestions |
| 10 | Generate Report | Assemble output: markdown report, JSON, or PR comment |

## Supported Platforms

- GitHub Actions

## Running Tests

```bash
python -m pytest tests/ -v
```
