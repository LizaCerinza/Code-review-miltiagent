"""Cliente mínimo de la API REST de GitHub para leer el PR y publicar la revisión."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .diff import ChangedFile

DEFAULT_API_URL = "https://api.github.com"


class GitHubClient:
    def __init__(
        self,
        token: str,
        repo: str,
        api_url: str = DEFAULT_API_URL,
        transport: httpx.BaseTransport | None = None,
    ):
        self.repo = repo
        self._http = httpx.Client(
            base_url=api_url,
            timeout=30.0,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def close(self) -> None:
        self._http.close()

    # ---- lectura -----------------------------------------------------------

    def get_pull(self, pr: int) -> dict[str, Any]:
        return self._request("GET", f"/repos/{self.repo}/pulls/{pr}")

    def list_files(self, pr: int) -> list[ChangedFile]:
        return [
            ChangedFile(path=item["filename"], status=item["status"], patch=item.get("patch", ""))
            for item in self._paginate(f"/repos/{self.repo}/pulls/{pr}/files")
        ]

    def list_tree_paths(self, sha: str) -> list[str]:
        """Rutas de todos los archivos del repo en un commit."""
        tree = self._request("GET", f"/repos/{self.repo}/git/trees/{sha}",
                             params={"recursive": "1"})
        return [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]

    def get_file_text(self, path: str, ref: str) -> str:
        data = self._request("GET", f"/repos/{self.repo}/contents/{path}", params={"ref": ref})
        return base64.b64decode(data["content"]).decode("utf-8")

    def list_review_comments(self, pr: int) -> list[dict[str, Any]]:
        return self._paginate(f"/repos/{self.repo}/pulls/{pr}/comments")

    def list_issue_comments(self, pr: int) -> list[dict[str, Any]]:
        return self._paginate(f"/repos/{self.repo}/issues/{pr}/comments")

    # ---- escritura ---------------------------------------------------------

    def create_issue_comment(self, pr: int, body: str) -> None:
        self._request("POST", f"/repos/{self.repo}/issues/{pr}/comments", json={"body": body})

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self._request("PATCH", f"/repos/{self.repo}/issues/comments/{comment_id}",
                      json={"body": body})

    def create_review(
        self, pr: int, commit_id: str, body: str, comments: list[dict[str, Any]]
    ) -> None:
        self._request(
            "POST",
            f"/repos/{self.repo}/pulls/{pr}/reviews",
            json={"commit_id": commit_id, "body": body, "event": "COMMENT", "comments": comments},
        )

    # ---- helpers -----------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._http.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def _paginate(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._request("GET", path, params={"per_page": 100, "page": page})
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1
