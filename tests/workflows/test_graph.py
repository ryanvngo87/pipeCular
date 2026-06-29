from unittest.mock import MagicMock, call, patch

from app.workflows.graph import run_pipeline, _PIPELINE


def test_pipeline_has_nine_nodes():
    assert len(_PIPELINE) == 9


def test_run_pipeline_threads_state_through_all_nodes():
    # Each mock node returns the state it received, plus a marker so we can
    # verify the chain: node N sees the output of node N-1.
    call_log: list[str] = []

    def make_node(name: str):
        def node(state):
            call_log.append(name)
            return {**state, f"visited_{name}": True}
        node.__name__ = name
        return node

    mock_nodes = [make_node(f"node_{i}") for i in range(9)]

    with patch("app.workflows.graph._PIPELINE", mock_nodes):
        result = run_pipeline("https://github.com/o/r/actions/runs/1")

    assert call_log == [f"node_{i}" for i in range(9)]
    assert all(result.get(f"visited_node_{i}") for i in range(9))


def test_run_pipeline_sets_raw_input():
    first_seen: list[dict] = []

    def capture_node(state):
        first_seen.append(state)
        return state

    with patch("app.workflows.graph._PIPELINE", [capture_node]):
        run_pipeline("https://github.com/o/r/actions/runs/99")

    assert first_seen[0]["raw_input"] == "https://github.com/o/r/actions/runs/99"


def test_run_pipeline_returns_final_state():
    def identity(state):
        return state

    with patch("app.workflows.graph._PIPELINE", [identity]):
        result = run_pipeline("input")

    assert result["raw_input"] == "input"
