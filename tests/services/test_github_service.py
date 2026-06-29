import pytest
from unittest.mock import MagicMock

import httpx

from app.services.github_service import GitHubService


def _make_service(token=None):
    svc = GitHubService(token=token)
    return svc


def _mock_response(json_data=None, text=None, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or ""
    resp.raise_for_status = MagicMock()
    return resp


def test_get_run_calls_correct_url():
    svc = _make_service()
    svc._client.get = MagicMock(return_value=_mock_response({"id": 1}))

    svc.get_run("octocat", "hello-world", "42")

    svc._client.get.assert_called_once_with("/repos/octocat/hello-world/actions/runs/42")


def test_get_run_returns_json():
    svc = _make_service()
    payload = {"id": 42, "status": "completed", "conclusion": "failure"}
    svc._client.get = MagicMock(return_value=_mock_response(payload))

    result = svc.get_run("owner", "repo", "42")

    assert result == payload


def test_get_run_raises_on_http_error():
    svc = _make_service()
    resp = _mock_response(status_code=404)
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=resp
    )
    svc._client.get = MagicMock(return_value=resp)

    with pytest.raises(httpx.HTTPStatusError):
        svc.get_run("owner", "repo", "99")


def test_get_run_jobs_calls_correct_url():
    svc = _make_service()
    svc._client.get = MagicMock(return_value=_mock_response({"jobs": []}))

    svc.get_run_jobs("octocat", "hello-world", "42")

    svc._client.get.assert_called_once_with(
        "/repos/octocat/hello-world/actions/runs/42/jobs"
    )


def test_get_run_jobs_returns_json():
    svc = _make_service()
    payload = {"total_count": 1, "jobs": [{"id": 1, "name": "build"}]}
    svc._client.get = MagicMock(return_value=_mock_response(payload))

    result = svc.get_run_jobs("owner", "repo", "42")

    assert result["jobs"][0]["name"] == "build"


def test_get_job_logs_calls_correct_url_with_redirect():
    svc = _make_service()
    svc._client.get = MagicMock(return_value=_mock_response(text="log output"))

    svc.get_job_logs("octocat", "hello-world", 7)

    svc._client.get.assert_called_once_with(
        "/repos/octocat/hello-world/actions/jobs/7/logs",
        follow_redirects=True,
    )


def test_get_job_logs_returns_text():
    svc = _make_service()
    svc._client.get = MagicMock(return_value=_mock_response(text="##[error]something failed"))

    result = svc.get_job_logs("owner", "repo", 7)

    assert result == "##[error]something failed"


def test_auth_header_set_when_token_provided():
    svc = GitHubService(token="ghp_abc123")
    assert svc._client.headers["Authorization"] == "Bearer ghp_abc123"


def test_no_auth_header_without_token():
    svc = GitHubService()
    assert "Authorization" not in svc._client.headers


def test_context_manager_closes_client():
    svc = GitHubService()
    svc._client.close = MagicMock()
    with svc:
        pass
    svc._client.close.assert_called_once()
