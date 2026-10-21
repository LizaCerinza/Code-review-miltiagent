import json

import httpx
import pytest

from reviewer.diff import ChangedFile
from reviewer.github import GitHubClient
from reviewer.models import AgentReport, Finding, ReviewResult
from reviewer.publisher import publish


class FakeGitHub:
    """Simula los endpoints de comentarios de un PR guardando el estado en memoria."""

    def __init__(self, review_status=200):
        self.issue_comments: list[dict] = []
        self.review_comments: list[dict] = []
        self.review_status = review_status
        self.reviews = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path.endswith("/issues/5/comments") and method == "GET":
            return httpx.Response(200, json=self.issue_comments)
        if path.endswith("/issues/5/comments") and method == "POST":
            body = json.loads(request.content)["body"]
            self.issue_comments.append({"id": len(self.issue_comments) + 1, "body": body})
            return httpx.Response(201, json={})
        if "/issues/comments/" in path and method == "PATCH":
            cid = int(path.rsplit("/", 1)[1])
            next(c for c in self.issue_comments if c["id"] == cid)["body"] = json.loads(
                request.content)["body"]
            return httpx.Response(200, json={})
        if path.endswith("/pulls/5/comments"):
            return httpx.Response(200, json=self.review_comments)
        if path.endswith("/pulls/5/reviews"):
            if self.review_status != 200:
                return httpx.Response(self.review_status, json={"message": "invalid line"})
            self.reviews += 1
            self.review_comments.extend(json.loads(request.content)["comments"])
            return httpx.Response(200, json={})
        return httpx.Response(404)

    def client(self) -> GitHubClient:
        return GitHubClient("t", "o/r", transport=httpx.MockTransport(self.handler))


FILES = [ChangedFile("src/a.ts", "modified", "@@ -1,2 +1,3 @@\n a\n+b\n+c")]


def result():
    def f(line, title):
        return Finding(file="src/a.ts", line=line, severity="major", title=title, message="m",
                       evidence="e", agents=["design"])
    return ReviewResult(reports=[AgentReport(agent="design")],
                        findings=[f(2, "en el diff"), f(50, "fuera del diff")],
                        fail_on="critical", blocking=False, incomplete=False)


def test_second_run_edits_summary_and_does_not_repeat_inline():
    fake = FakeGitHub()
    gh = fake.client()

    assert publish(gh, 5, "sha", result(), FILES) == 1
    assert publish(gh, 5, "sha", result(), FILES) == 0

    assert len(fake.issue_comments) == 1
    assert fake.reviews == 1
    assert [c["line"] for c in fake.review_comments] == [2]
    # El hallazgo fuera del diff aparece solo en el resumen.
    assert "fuera del diff" in fake.issue_comments[0]["body"]


def test_422_publishes_only_summary():
    fake = FakeGitHub(review_status=422)
    assert publish(fake.client(), 5, "sha", result(), FILES) == 0
    assert len(fake.issue_comments) == 1


def test_other_http_errors_propagate():
    fake = FakeGitHub(review_status=500)
    with pytest.raises(httpx.HTTPStatusError):
        publish(fake.client(), 5, "sha", result(), FILES)
