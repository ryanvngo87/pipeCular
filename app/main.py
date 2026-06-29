import sys

from app.workflows.graph import run_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.main <pipeline-url-or-run-id>", file=sys.stderr)
        sys.exit(1)

    raw_input = sys.argv[1]
    try:
        state = run_pipeline(raw_input)
        print(state.get("report") or "No report generated.")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
