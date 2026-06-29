import os

import anthropic

from app.models.pipeline import PipelineRun
from app.workflows.state import WorkflowState

_MODEL = "claude-sonnet-4-6"


def _build_prompt(state: WorkflowState) -> str:
    pipeline_run: PipelineRun | None = state.get("pipeline_run")

    failed_jobs_lines: list[str] = []
    if pipeline_run:
        for job in pipeline_run.jobs:
            if job.status == "failure":
                failed_steps = [s.name for s in job.steps if s.status == "failure"]
                failed_jobs_lines.append(
                    f"- Job: {job.name}, Failed steps: {', '.join(failed_steps) or 'none'}"
                )

    repo_context = state.get("repo_context") or {}
    context_section = ""
    if repo_context:
        snippets = [f"### {path}\n```\n{content[:2000]}\n```" for path, content in repo_context.items()]
        context_section = "\n\n## Relevant Source Files\n" + "\n\n".join(snippets)

    return f"""You are a CI/CD failure analyst. Identify the root cause of this pipeline failure.

## Pipeline
- Repository: {state.get('owner', '?')}/{state.get('repo', '?')}
- Platform: {state.get('platform', '?')}
- Failure category: {state.get('failure_category', 'unknown')}

## Failed Jobs
{chr(10).join(failed_jobs_lines) or 'No job details available'}

## Error Output
{state.get('failure_reason') or 'No error output available'}
{context_section}

Provide a concise root cause analysis in 2-4 sentences. Focus on WHY the failure occurred."""


def analyze_root_cause(state: WorkflowState) -> WorkflowState:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": _build_prompt(state)}],
    )
    return {**state, "root_cause": message.content[0].text.strip()}
