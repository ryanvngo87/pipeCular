from app.workflows.state import WorkflowState


def generate_report(state: WorkflowState) -> WorkflowState:
    pipeline_run = state.get("pipeline_run")
    owner = state.get("owner", "?")
    repo = state.get("repo", "?")
    run_id = state.get("run_id", "?")
    platform = state.get("platform", "?")
    status = pipeline_run.status if pipeline_run else "unknown"

    lines = [
        "# Pipeline Failure Report",
        "",
        f"**Repository:** {owner}/{repo}",
        f"**Run ID:** {run_id}",
        f"**Platform:** {platform}",
        f"**Status:** {status}",
        "",
        "## Failed Jobs",
    ]

    if pipeline_run:
        failed_jobs = [j for j in pipeline_run.jobs if j.status == "failure"]
        if failed_jobs:
            for job in failed_jobs:
                lines.append(f"\n### {job.name}")
                for step in job.steps:
                    if step.status == "failure":
                        lines.append(f"- **Failed step:** {step.name}")
                        if step.error_output:
                            snippet = step.error_output[:300]
                            lines.append(f"  ```\n  {snippet}\n  ```")
        else:
            lines.append("\n_No failed jobs found._")

    lines += [
        "",
        "## Failure Classification",
        f"**Category:** {state.get('failure_category', 'unknown')}",
        "",
        "## Root Cause",
        state.get("root_cause") or "_Not analyzed_",
        "",
        "## Suggested Fix",
        state.get("suggested_fix") or "_No suggestions available_",
    ]

    return {**state, "report": "\n".join(lines)}
