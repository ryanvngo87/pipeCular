import os

import anthropic

from app.workflows.state import WorkflowState

_MODEL = "claude-sonnet-4-6"


def _build_prompt(state: WorkflowState) -> str:
    repo_context = state.get("repo_context") or {}
    context_section = ""
    if repo_context:
        snippets = [f"### {path}\n```\n{content[:2000]}\n```" for path, content in repo_context.items()]
        context_section = "\n\n## Relevant Source Files\n" + "\n\n".join(snippets)

    return f"""You are a CI/CD failure analyst. Suggest specific fixes for this pipeline failure.

## Root Cause
{state.get('root_cause') or 'Unknown'}

## Error Output
{state.get('failure_reason') or 'No error output available'}

## Failure Category
{state.get('failure_category', 'unknown')}
{context_section}

Provide 2-3 specific, actionable fix suggestions. Include code snippets where helpful. Be concise."""


def suggest_fix(state: WorkflowState) -> WorkflowState:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": _build_prompt(state)}],
    )
    return {**state, "suggested_fix": message.content[0].text.strip()}
