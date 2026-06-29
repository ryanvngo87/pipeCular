import base64
from typing import Any

import httpx


class GitHubService:
    _BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=self._BASE_URL, headers=headers)

    def get_run(self, owner: str, repo: str, run_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}")
        resp.raise_for_status()
        return resp.json()

    def get_run_jobs(self, owner: str, repo: str, run_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")
        resp.raise_for_status()
        return resp.json()

    def get_job_logs(self, owner: str, repo: str, job_id: int) -> str:
        resp = self._client.get(
            f"/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    def get_file_content(self, owner: str, repo: str, path: str) -> str:
        resp = self._client.get(f"/repos/{owner}/{repo}/contents/{path}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
        return data.get("content", "")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubService":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
