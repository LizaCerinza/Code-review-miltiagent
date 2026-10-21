import httpx

from reviewer.sonar import fetch_pr_issues, read_project_key


def test_read_project_key(tmp_path):
    (tmp_path / "sonar-project.properties").write_text(
        "# comentario\nsonar.projectKey=farsov_Code-review-miltiagent\nsonar.sources=src\n",
        encoding="utf-8",
    )
    assert read_project_key(tmp_path) == "farsov_Code-review-miltiagent"
    assert read_project_key(tmp_path / "otro") is None


def test_fetch_pr_issues_maps_fields_and_sends_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"issues": [{
            "rule": "typescript:S2068", "severity": "BLOCKER", "type": "VULNERABILITY",
            "component": "key:src/config/env.config.ts", "line": 10, "message": "secret",
        }]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    issues = fetch_pr_issues("https://sonarcloud.io/", "tok", "key", 7, client=client)

    assert issues == [{"rule": "typescript:S2068", "severity": "BLOCKER", "type": "VULNERABILITY",
                       "file": "src/config/env.config.ts", "line": 10, "message": "secret"}]
    assert seen["auth"] == "Bearer tok"
    assert seen["params"]["pullRequest"] == "7"
    assert seen["params"]["componentKeys"] == "key"


def test_fetch_pr_issues_returns_none_on_error():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    assert fetch_pr_issues("https://sonarcloud.io", "tok", "key", 7, client=client) is None
